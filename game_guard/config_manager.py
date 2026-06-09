"""Gestión de configuración y autenticación del administrador."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

APP_NAME = "GameGuard"
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
    day_id: {
        "enabled": False,
        "all_day": False,
        "start": "18:00",
        "end": "22:00",
    }
    for day_id, _ in DAYS
}


def _default_config() -> dict[str, Any]:
    return {
        "setup_complete": False,
        "admin_password_hash": "",
        "admin_salt": "",
        "enabled": True,
        "blocked_apps": [],
        "schedule": deepcopy(DEFAULT_SCHEDULE),
    }


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()


class ConfigManager:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load()

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
    def config(self) -> dict[str, Any]:
        return self._config

    @property
    def is_setup_complete(self) -> bool:
        return bool(self._config.get("setup_complete"))

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.get("enabled", True))

    def set_enabled(self, enabled: bool) -> None:
        self._config["enabled"] = enabled
        self.save()

    def verify_password(self, password: str) -> bool:
        salt = self._config.get("admin_salt", "")
        stored = self._config.get("admin_password_hash", "")
        if not salt or not stored:
            return False
        return secrets.compare_digest(_hash_password(password, salt), stored)

    def set_admin_password(self, password: str) -> None:
        salt = secrets.token_hex(16)
        self._config["admin_salt"] = salt
        self._config["admin_password_hash"] = _hash_password(password, salt)
        self._config["setup_complete"] = True
        self.save()

    def get_blocked_apps(self) -> list[dict[str, str]]:
        return list(self._config.get("blocked_apps", []))

    def add_blocked_app(self, name: str, exe_path: str) -> bool:
        exe_name = Path(exe_path).name.lower()
        for app in self._config["blocked_apps"]:
            if app["exe_name"] == exe_name:
                return False
        self._config["blocked_apps"].append(
            {
                "name": name,
                "exe_path": exe_path,
                "exe_name": exe_name,
            }
        )
        self.save()
        return True

    def remove_blocked_app(self, exe_name: str) -> None:
        self._config["blocked_apps"] = [
            app
            for app in self._config["blocked_apps"]
            if app["exe_name"] != exe_name.lower()
        ]
        self.save()

    def get_schedule(self) -> dict[str, dict[str, Any]]:
        return self._config["schedule"]

    def update_schedule(self, schedule: dict[str, dict[str, Any]]) -> None:
        self._config["schedule"] = schedule
        self.save()

    def is_play_allowed_now(self, now: datetime | None = None) -> bool:
        if not self.is_enabled:
            return True

        current = now or datetime.now()
        day_id = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ][current.weekday()]
        day_cfg = self._config["schedule"].get(day_id, {})

        if not day_cfg.get("enabled"):
            return False
        if day_cfg.get("all_day"):
            return True

        start = day_cfg.get("start", "00:00")
        end = day_cfg.get("end", "23:59")
        current_time = current.strftime("%H:%M")
        return start <= current_time <= end

    def next_allowed_window_text(self, now: datetime | None = None) -> str:
        current = now or datetime.now()
        if self.is_play_allowed_now(current):
            return "Ahora puedes jugar"

        day_names = dict(DAYS)
        for offset in range(8):
            check = datetime(
                current.year,
                current.month,
                current.day,
                current.hour,
                current.minute,
            )
            if offset:
                from datetime import timedelta

                check = check + timedelta(days=offset)

            day_id = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ][check.weekday()]
            day_cfg = self._config["schedule"].get(day_id, {})
            if not day_cfg.get("enabled"):
                continue

            if day_cfg.get("all_day"):
                if offset == 0:
                    return f"Hoy ({day_names[day_id]}) todo el día"
                return f"{day_names[day_id]} todo el día"

            start = day_cfg.get("start", "00:00")
            end = day_cfg.get("end", "23:59")
            check_time = check.strftime("%H:%M")

            if offset == 0 and check_time < start:
                return f"Hoy desde las {start} hasta las {end}"
            if offset > 0:
                return f"{day_names[day_id]} de {start} a {end}"

        return "Sin horarios configurados"
