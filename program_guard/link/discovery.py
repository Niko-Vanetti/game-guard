"""Descubrimiento LAN por UDP — mismo código en la red local."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 9848
MAGIC = b"PGLAN1"
TTL = 8.0


def broadcast_session(code: str, host: str, port: int, token: str, stop: threading.Event) -> None:
    payload = json.dumps({"code": code, "host": host, "port": port, "token": token}).encode("utf-8")
    message = MAGIC + payload
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while not stop.wait(2.0):
            try:
                sock.sendto(message, ("255.255.255.255", DISCOVERY_PORT))
            except OSError:
                logger.debug("Broadcast falló")
    finally:
        sock.close()


def find_session(code: str, timeout: float = 5.0) -> dict | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    deadline = time.time() + timeout
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(0.5)
        while time.time() < deadline:
            try:
                data, _addr = sock.recvfrom(4096)
            except TimeoutError:
                continue
            except OSError:
                break
            if not data.startswith(MAGIC):
                continue
            try:
                info = json.loads(data[len(MAGIC) :].decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if info.get("code") == code:
                return info
    finally:
        sock.close()
    return None


def start_broadcast(code: str, host: str, port: int, token: str) -> tuple[threading.Event, threading.Thread]:
    stop = threading.Event()
    thread = threading.Thread(target=broadcast_session, args=(code, host, port, token, stop), daemon=True)
    thread.start()
    return stop, thread
