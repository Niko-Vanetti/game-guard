"""Protocolo TCP local — mensajes JSON con prefijo de longitud."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any


def encode_message(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return struct.pack(">I", len(body)) + body


def decode_message(data: bytes) -> tuple[dict[str, Any], bytes]:
    if len(data) < 4:
        return {}, data
    length = struct.unpack(">I", data[:4])[0]
    if len(data) < 4 + length:
        return {}, data
    body = data[4 : 4 + length]
    rest = data[4 + length :]
    return json.loads(body.decode("utf-8")), rest


def send_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    sock.sendall(encode_message(payload))


def recv_message(sock: socket.socket) -> dict[str, Any]:
    buffer = b""
    while True:
        if len(buffer) >= 4:
            length = struct.unpack(">I", buffer[:4])[0]
            if len(buffer) >= 4 + length:
                msg, _ = decode_message(buffer)
                return msg
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Conexión cerrada")
        buffer += chunk


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.168.1.1", 1))
            return sock.getsockname()[0]
    except OSError:
        pass
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except OSError:
        return "127.0.0.1"
