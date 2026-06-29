"""Servidor embebido PG-Link — corre dentro de Admin o Cliente."""

from __future__ import annotations

import json
import logging
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

logger = logging.getLogger(__name__)

ROOM_TTL = 86400 * 2


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _merge_room(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


class _LinkHandler(BaseHTTPRequestHandler):
    server_version = "PG-Link/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_token(self, code: str) -> bool:
        host: EmbeddedHost = self.server.pg_host  # type: ignore[attr-defined]
        room = host.rooms.get(code)
        if not room:
            return False
        token = self.headers.get("X-PG-Token", "")
        return token == room.get("token")

    def do_GET(self) -> None:
        if not self.path.startswith("/rooms/") or not self.path.endswith(".json"):
            self._send_json(404, {"error": "not found"})
            return
        code = self.path[len("/rooms/") : -len(".json")]
        host: EmbeddedHost = self.server.pg_host  # type: ignore[attr-defined]
        with host.lock:
            room = host.rooms.get(code)
        if room is None:
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, room)

    def do_PUT(self) -> None:
        if not self.path.startswith("/rooms/") or not self.path.endswith(".json"):
            self._send_json(404, {"error": "not found"})
            return
        code = self.path[len("/rooms/") : -len(".json")]
        if not self._check_token(code):
            self._send_json(403, {"error": "token"})
            return
        payload = self._read_body()
        payload.setdefault("code", code)
        payload.setdefault("created_at", time.time())
        host: EmbeddedHost = self.server.pg_host  # type: ignore[attr-defined]
        with host.lock:
            host.rooms[code] = payload
        self._send_json(200, payload)

    def do_PATCH(self) -> None:
        if not self.path.startswith("/rooms/") or not self.path.endswith(".json"):
            self._send_json(404, {"error": "not found"})
            return
        code = self.path[len("/rooms/") : -len(".json")]
        if not self._check_token(code):
            self._send_json(403, {"error": "token"})
            return
        patch = self._read_body()
        host: EmbeddedHost = self.server.pg_host  # type: ignore[attr-defined]
        with host.lock:
            room = host.rooms.get(code)
            if room is None:
                self._send_json(404, {"error": "not found"})
                return
            host.rooms[code] = _merge_room(room, patch)
            updated = host.rooms[code]
        self._send_json(200, updated)


class EmbeddedHost:
    _instance: EmbeddedHost | None = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.rooms: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.port = 0
        self._http: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._broadcast_stop: threading.Event | None = None

    @classmethod
    def get(cls) -> EmbeddedHost:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = EmbeddedHost()
            return cls._instance

    def ensure_running(self) -> int:
        if self._http and self.port:
            return self.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        self._http = ThreadingHTTPServer(("0.0.0.0", self.port), _LinkHandler)
        self._http.pg_host = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()
        logger.info("PG-Link host en puerto %s", self.port)
        return self.port

    @property
    def local_address(self) -> str:
        return _local_ip()

    def create_room(
        self,
        code: str,
        token: str,
        creator: str,
        client_id: str = "",
        client_name: str = "",
    ) -> dict[str, Any]:
        self.ensure_running()
        payload = {
            "code": code,
            "token": token,
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
        with self.lock:
            self.rooms[code] = payload
        self._start_broadcast(code, token)
        return payload

    def _start_broadcast(self, code: str, token: str) -> None:
        from program_guard.link.discovery import start_broadcast

        if self._broadcast_stop:
            self._broadcast_stop.set()
        self._broadcast_stop, _ = start_broadcast(code, self.local_address, self.port, token)

    def stop_broadcast(self) -> None:
        if self._broadcast_stop:
            self._broadcast_stop.set()
            self._broadcast_stop = None

    def purge_old(self) -> None:
        cutoff = time.time() - ROOM_TTL
        with self.lock:
            expired = [c for c, r in self.rooms.items() if r.get("created_at", 0) < cutoff]
            for code in expired:
                del self.rooms[code]
