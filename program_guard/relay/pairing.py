"""Enlace por código vía relay propio (redes distintas, sin Firebase)."""

from __future__ import annotations

import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_RELAY_URL = "http://127.0.0.1:8765"


def load_relay_settings() -> dict[str, Any]:
    from program_guard.config_manager import CONFIG_DIR

    paths = [
        CONFIG_DIR / "relay_config.json",
        Path(__file__).resolve().parents[2] / "relay_config.json",
    ]
    for path in paths:
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        return data
            except (json.JSONDecodeError, OSError):
                logger.warning("No se pudo leer %s", path)
    return {"relay_url": DEFAULT_RELAY_URL}


class PairingService:
    ONLINE_SECONDS = 25

    def __init__(self, relay_url: str) -> None:
        if not relay_url:
            raise ValueError("Falta relay_url en relay_config.json")
        self.base = relay_url.rstrip("/")

    def _url(self, code: str) -> str:
        return f"{self.base}/rooms/{code}.json"

    def _generate_code(self) -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"

    def create_room(self, creator: str, client_id: str = "", client_name: str = "") -> str:
        for _ in range(12):
            code = self._generate_code()
            if self.get_room(code):
                continue
            payload = {
                "code": code,
                "created_by": creator,
                "created_at": time.time(),
                "linked": False,
                "admin_connected": False,
                "disconnect_by_admin": False,
                "client_id": client_id,
                "client_name": client_name,
                "config": {
                    "enabled": True,
                    "blocked_apps": [],
                    "schedule": {},
                    "pause_until": None,
                    "tagged_games": [],
                },
                "command": None,
                "client_telemetry": {},
            }
            requests.put(self._url(code), json=payload, timeout=12)
            return code
        raise RuntimeError("No se pudo generar código único")

    def join_room(self, code: str, joiner: str) -> dict[str, Any] | None:
        room = self.get_room(code)
        if not room:
            return None
        patch: dict[str, Any] = {"linked": True, f"{joiner}_joined_at": time.time()}
        if joiner == "admin":
            patch["admin_connected"] = True
            patch["disconnect_by_admin"] = False
        requests.patch(self._url(code), json=patch, timeout=12)
        return self.get_room(code)

    def get_room(self, code: str) -> dict[str, Any] | None:
        try:
            response = requests.get(self._url(code), timeout=12)
        except requests.RequestException:
            logger.exception("Error leyendo sala %s", code)
            return None
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None

    def patch_room(self, code: str, payload: dict[str, Any]) -> None:
        requests.patch(self._url(code), json=payload, timeout=12)

    def send_command(self, code: str, command: dict[str, Any]) -> None:
        command["requested_at"] = time.time()
        self.patch_room(code, {"command": command})

    def clear_command(self, code: str) -> None:
        self.patch_room(code, {"command": None})

    def update_config(self, code: str, config: dict[str, Any]) -> None:
        self.patch_room(code, {"config": config})

    def push_telemetry(self, code: str, telemetry: dict[str, Any]) -> None:
        telemetry["last_seen"] = time.time()
        self.patch_room(code, {"client_telemetry": telemetry})

    def disconnect_admin(self, code: str) -> None:
        self.patch_room(
            code,
            {
                "linked": False,
                "admin_connected": False,
                "disconnect_by_admin": True,
            },
        )

    @classmethod
    def client_online(cls, room: dict[str, Any] | None) -> bool:
        if not room:
            return False
        telemetry = room.get("client_telemetry") or {}
        last = telemetry.get("last_seen")
        if not last:
            return False
        return (time.time() - float(last)) <= cls.ONLINE_SECONDS
