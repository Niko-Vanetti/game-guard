"""Configuración local — Program Guard."""

from __future__ import annotations

import json
import os
import secrets
import string
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

APP_NAME = "ProgramGuard"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

DAYS = [
    ("monday", "Lunes"),
    ("tuesday", "Martes"),
    ("wednesday", "Miércoles"),
    ("thursday", "Jueves"),
    ("friday", "Viernes"),
    ("saturday", "Sábado"),
    ("sunday", "Domingo"),
]

DEFAULT_SCHEDULE = {
    day_id: {"enabled": False, "all_day": False, "start": "18:00", "end": "22:00"}
    for day_id, _ in DAYS
}

SCHEDULE_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "weekend_only": {
        day_id: {
            "enabled": day_id in ("friday", "saturday", "sunday"),
            "all_day": day_id == "friday",
            "start": "14:00" if day_id in ("saturday", "sunday") else "18:00",
            "end": "22:00",
        }
        for day_id, _ in DAYS
    },
    "evenings": {
        day_id: {
            "enabled": day_id in ("friday", "saturday", "sunday"),
            "all_day": False,
            "start": "18:00",
            "end": "22:00",
        }
        for day_id, _ in DAYS
    },
    "school_days": {
        day_id: {
            "enabled": day_id in ("friday", "saturday"),
            "all_day": False,
            "start": "16:00" if day_id == "friday" else "10:00",
            "end": "20:00" if day_id == "friday" else "22:00",
        }
        for day_id, _ in DAYS
    },
}


def _generate_id(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def _default_config() -> dict[str, Any]:
    return {
        "device_id": "",
        "device_name": "",
        "active_room_code": "",
        "active_link_host": "",
        "active_link_token": "",
        "tagged_games": [],
        "enabled": True,
        "theme": "dark",
        "monitor_interval": 2.0,
        "pause_until": None,
        "blocked_apps": [],
        "schedule": deepcopy(DEFAULT_SCHEDULE),
    }


class ConfigManager:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load()
        self.ensure_device_id()

    def _load(self) -> dict[str, Any]:
        if not CONFIG_FILE.exists():
            return _default_config()
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return _default_config()
        merged = _default_config()
        merged.update(data)
        for day_id, _ in DAYS:
            merged["schedule"].setdefault(day_id, deepcopy(DEFAULT_SCHEDULE[day_id]))
        return merged

    def save(self) -> None:
        with CONFIG_FILE.open("w", encoding="utf-8") as handle:
            json.dump(self._config, handle, indent=2, ensure_ascii=False)

    @property
    def device_id(self) -> str:
        return self._config.get("device_id", "")

    @property
    def device_name(self) -> str:
        return self._config.get("device_name") or f"PC-{self.device_id}"

    @property
    def active_link_host(self) -> str:
        return self._config.get("active_link_host", "")

    @property
    def active_link_token(self) -> str:
        return self._config.get("active_link_token", "")

    @property
    def active_room_code(self) -> str:
        return self._config.get("active_room_code", "")

    @property
    def tagged_games(self) -> list[str]:
        return list(self._config.get("tagged_games", []))

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.get("enabled", True))

    @property
    def theme(self) -> str:
        v = self._config.get("theme", "dark")
        return v if v in ("light", "dark") else "dark"

    @property
    def monitor_interval(self) -> float:
        return float(self._config.get("monitor_interval", 2.0))

    @property
    def pause_until(self) -> str | None:
        return self._config.get("pause_until")

    def ensure_device_id(self) -> str:
        if not self._config.get("device_id"):
            self._config["device_id"] = _generate_id(8)
            self.save()
        return self._config["device_id"]

    def set_active_link(self, code: str, host: str = "", token: str = "") -> None:
        self._config["active_room_code"] = code
        self._config["active_link_host"] = host
        self._config["active_link_token"] = token
        self.save()

    def set_active_room(self, code: str) -> None:
        self.set_active_link(code)

    def clear_active_room(self) -> None:
        self._config["active_room_code"] = ""
        self._config["active_link_host"] = ""
        self._config["active_link_token"] = ""
        self.save()

    def set_enabled(self, enabled: bool) -> None:
        self._config["enabled"] = enabled
        if enabled:
            self._config["pause_until"] = None
        self.save()

    def pause_for_minutes(self, minutes: int) -> None:
        from datetime import timedelta

        self._config["pause_until"] = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
        self._config["enabled"] = True
        self.save()

    def clear_pause(self) -> None:
        self._config["pause_until"] = None
        self.save()

    def is_paused(self, now: datetime | None = None) -> bool:
        raw = self._config.get("pause_until")
        if not raw:
            return False
        try:
            until = datetime.fromisoformat(raw)
        except ValueError:
            self.clear_pause()
            return False
        if (now or datetime.now()) >= until:
            self.clear_pause()
            return False
        return True

    def pause_remaining_text(self, now: datetime | None = None) -> str:
        if not self.is_paused(now):
            return ""
        raw = self._config.get("pause_until", "")
        try:
            until = datetime.fromisoformat(raw)
            mins = int((until - (now or datetime.now())).total_seconds() // 60)
            return f"Pausa — {mins} min" if mins < 60 else f"Pausa — {mins // 60}h {mins % 60}m"
        except ValueError:
            return "En pausa"

    def to_remote_config(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled,
            "monitor_interval": self.monitor_interval,
            "pause_until": self.pause_until,
            "blocked_apps": self.get_blocked_apps(),
            "schedule": deepcopy(self.get_schedule()),
            "tagged_games": self.tagged_games,
        }

    def apply_remote_config(self, remote: dict[str, Any]) -> None:
        for key in ("enabled", "monitor_interval", "pause_until", "blocked_apps", "schedule", "tagged_games"):
            if key in remote:
                self._config[key] = remote[key]
        for day_id, _ in DAYS:
            self._config["schedule"].setdefault(day_id, deepcopy(DEFAULT_SCHEDULE[day_id]))
        self.save()

    def get_blocked_apps(self) -> list[dict[str, str]]:
        return list(self._config.get("blocked_apps", []))

    def add_blocked_app(self, name: str, exe_path: str = "", exe_name: str = "") -> bool:
        exe_name = (Path(exe_path).name if exe_path else exe_name).lower().strip()
        if not exe_name:
            return False
        if any(a["exe_name"] == exe_name for a in self._config["blocked_apps"]):
            return False
        self._config["blocked_apps"].append({"name": name, "exe_path": exe_path, "exe_name": exe_name})
        self.save()
        return True

    def remove_blocked_app(self, exe_name: str) -> None:
        exe = exe_name.lower()
        self._config["blocked_apps"] = [a for a in self._config["blocked_apps"] if a["exe_name"] != exe]
        self.save()

    def get_schedule(self) -> dict[str, dict[str, Any]]:
        return self._config["schedule"]

    def is_play_allowed_now(self, now: datetime | None = None) -> bool:
        if not self.is_enabled or self.is_paused(now):
            return True
        current = now or datetime.now()
        day_id = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][current.weekday()]
        day_cfg = self._config["schedule"].get(day_id, {})
        if not day_cfg.get("enabled"):
            return False
        if day_cfg.get("all_day"):
            return True
        t = current.strftime("%H:%M")
        return day_cfg.get("start", "00:00") <= t <= day_cfg.get("end", "23:59")

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled,
            "paused": self.is_paused(),
            "pause_text": self.pause_remaining_text(),
            "play_allowed": self.is_play_allowed_now(),
            "status_text": self._status_label(),
            "blocked_count": len(self.get_blocked_apps()),
        }

    def _status_label(self) -> str:
        if not self.is_enabled:
            return "Desactivado"
        if self.is_paused():
            return self.pause_remaining_text() or "En pausa"
        if self.is_play_allowed_now():
            return "Horario permitido"
        return "Bloqueando"
