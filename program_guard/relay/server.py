"""Relay HTTP mínimo — enlace por código sin Firebase (stdlib)."""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote

_rooms: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_ROOM_TTL = 86400 * 2  # 48 h


def _purge_old() -> None:
    cutoff = time.time() - _ROOM_TTL
    with _lock:
        expired = [code for code, room in _rooms.items() if room.get("created_at", 0) < cutoff]
        for code in expired:
            del _rooms[code]


def _merge_room(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


class RelayHandler(BaseHTTPRequestHandler):
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

    def _room_code(self) -> str | None:
        path = unquote(self.path.split("?", 1)[0])
        if not path.startswith("/rooms/") or not path.endswith(".json"):
            return None
        return path[len("/rooms/") : -len(".json")]

    def do_GET(self) -> None:
        code = self._room_code()
        if not code:
            self._send_json(404, {"error": "not found"})
            return
        with _lock:
            room = _rooms.get(code)
        if room is None:
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, room)

    def do_PUT(self) -> None:
        code = self._room_code()
        if not code:
            self._send_json(404, {"error": "not found"})
            return
        payload = self._read_body()
        payload.setdefault("code", code)
        payload.setdefault("created_at", time.time())
        with _lock:
            _rooms[code] = payload
        self._send_json(200, payload)

    def do_PATCH(self) -> None:
        code = self._room_code()
        if not code:
            self._send_json(404, {"error": "not found"})
            return
        patch = self._read_body()
        with _lock:
            room = _rooms.get(code)
            if room is None:
                self._send_json(404, {"error": "not found"})
                return
            _rooms[code] = _merge_room(room, patch)
            updated = _rooms[code]
        self._send_json(200, updated)


def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    def janitor() -> None:
        while True:
            time.sleep(3600)
            _purge_old()

    threading.Thread(target=janitor, daemon=True).start()
    server = ThreadingHTTPServer((host, port), RelayHandler)
    print(f"Program Guard Relay en http://{host}:{port}")
    print("Salas: GET/PUT/PATCH /rooms/{{codigo}}.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nRelay detenido.")
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Program Guard Relay")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
