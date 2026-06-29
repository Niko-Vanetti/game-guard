"""Conexión TCP desde el Admin hacia un Cliente en la red local."""

from __future__ import annotations

import socket
from typing import Any

from game_guard.network.protocol import recv_message, send_message


class AdminConnection:
    def __init__(self, host: str, port: int, token: str) -> None:
        self.host = host.strip()
        self.port = port
        self.token = token.strip().upper()
        self._sock: socket.socket | None = None
        self.device_name = ""

    def connect(self) -> None:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=6)
        sock.settimeout(12.0)
        self._sock = sock
        send_message(sock, {"type": "auth", "token": self.token})
        response = recv_message(sock)
        if response.get("type") == "error":
            raise ConnectionError(response.get("message", "Conexión rechazada"))
        if response.get("type") != "ok":
            raise ConnectionError("Respuesta inválida del cliente")
        self.device_name = response.get("name", self.host)

    def command(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._sock:
            raise ConnectionError("No conectado")
        send_message(self._sock, payload)
        return recv_message(self._sock)

    def get_status(self) -> dict[str, Any]:
        return self.command({"type": "get_status"})

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self) -> AdminConnection:
        self.connect()
        return self

    def __exit__(self, *_args) -> None:
        self.close()
