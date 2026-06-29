"""Sincronización automática PG — solo código, sin configuración externa."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from copy import deepcopy
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_PREFIX = "pguard/rooms/v1"


def _merge_room(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


class HubService:
    """Enlace por código de 6 dígitos — ambos dispositivos se conectan solos."""

    ONLINE_SECONDS = 25

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._subs: set[str] = set()
        self._lock = threading.Lock()
        client_id = f"pg-{secrets.token_hex(6)}"
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self._client.on_message = self._on_message
        self._client.connect(BROKER, PORT, keepalive=60)
        self._client.loop_start()

    @property
    def last_link_string(self) -> str:
        return ""

    def _topic(self, code: str) -> str:
        return f"{TOPIC_PREFIX}/{code}"

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        code = msg.topic.rsplit("/", 1)[-1]
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if isinstance(data, dict):
            with self._lock:
                self._cache[code] = data

    def _ensure_sub(self, code: str) -> None:
        if code in self._subs:
            return
        self._client.subscribe(self._topic(code), qos=1)
        self._subs.add(code)

    def _publish(self, code: str, data: dict[str, Any]) -> None:
        self._ensure_sub(code)
        with self._lock:
            self._cache[code] = data
        payload = json.dumps(data, ensure_ascii=False)
        self._client.publish(self._topic(code), payload, qos=1, retain=True)

    def _patch(self, code: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        room = self.get_room(code)
        if room is None:
            return None
        merged = _merge_room(room, patch)
        self._publish(code, merged)
        return merged

    def _generate_code(self) -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"

    def create_room(self, creator: str, client_id: str = "", client_name: str = "") -> str:
        for _ in range(16):
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
            self._publish(code, payload)
            return code
        raise RuntimeError("No se pudo generar código")

    def join_room(self, code: str, joiner: str) -> dict[str, Any] | None:
        room = self.get_room(code)
        if not room:
            return None
        patch: dict[str, Any] = {"linked": True, f"{joiner}_joined_at": time.time()}
        if joiner == "admin":
            patch["admin_connected"] = True
            patch["disconnect_by_admin"] = False
        return self._patch(code, patch)

    def get_room(self, code: str) -> dict[str, Any] | None:
        self._ensure_sub(code)
        with self._lock:
            cached = self._cache.get(code)
        if cached:
            return deepcopy(cached)
        for _ in range(10):
            time.sleep(0.4)
            with self._lock:
                cached = self._cache.get(code)
            if cached:
                return deepcopy(cached)
        return None

    def send_command(self, code: str, command: dict[str, Any]) -> None:
        command["requested_at"] = time.time()
        self._patch(code, {"command": command})

    def clear_command(self, code: str) -> None:
        self._patch(code, {"command": None})

    def update_config(self, code: str, config: dict[str, Any]) -> None:
        self._patch(code, {"config": config})

    def push_telemetry(self, code: str, telemetry: dict[str, Any]) -> None:
        telemetry["last_seen"] = time.time()
        self._patch(code, {"client_telemetry": telemetry})

    def disconnect_admin(self, code: str) -> None:
        self._patch(
            code,
            {
                "linked": False,
                "admin_connected": False,
                "disconnect_by_admin": True,
            },
        )

    def connect_to_saved(self, code: str, _link_host: str = "", _link_token: str = "") -> bool:
        return bool(self.get_room(code))

    @classmethod
    def client_online(cls, room: dict[str, Any] | None) -> bool:
        if not room:
            return False
        telemetry = room.get("client_telemetry") or {}
        last = telemetry.get("last_seen")
        if not last:
            return False
        return (time.time() - float(last)) <= cls.ONLINE_SECONDS


PairingService = HubService
LinkService = HubService
