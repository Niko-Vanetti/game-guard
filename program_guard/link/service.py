"""Servicio de enlace PG-Link — protocolo propio, sin relay ni Firebase."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any

import requests

from program_guard.link.discovery import find_session
from program_guard.link.format import ParsedLink, format_link, is_code_only, parse_link
from program_guard.link.host import EmbeddedHost

logger = logging.getLogger(__name__)


class LinkService:
    """Enlace dispositivo a dispositivo con código + clave + dirección del anfitrión."""

    ONLINE_SECONDS = 25

    def __init__(self) -> None:
        self._host = EmbeddedHost.get()
        self._remote_base = ""
        self._remote_token = ""
        self._last_link = ""

    @property
    def last_link_string(self) -> str:
        return self._last_link

    def _generate_code(self) -> str:
        return f"{secrets.randbelow(900000) + 100000:06d}"

    def _generate_token(self) -> str:
        return secrets.token_hex(4)

    def _use_remote(self, host: str, port: int, token: str) -> None:
        self._remote_base = f"http://{host}:{port}"
        self._remote_token = token

    def _use_local(self) -> None:
        self._remote_base = f"http://127.0.0.1:{self._host.ensure_running()}"
        self._remote_token = ""

    def _base(self) -> str:
        return self._remote_base or f"http://127.0.0.1:{self._host.port}"

    def _headers(self, token: str = "") -> dict[str, str]:
        tok = token or self._remote_token
        return {"X-PG-Token": tok} if tok else {}

    def _url(self, code: str) -> str:
        return f"{self._base().rstrip('/')}/rooms/{code}.json"

    def create_room(self, creator: str, client_id: str = "", client_name: str = "") -> str:
        for _ in range(12):
            code = self._generate_code()
            token = self._generate_token()
            with self._host.lock:
                if code in self._host.rooms:
                    continue
            self._host.create_room(code, token, creator, client_id, client_name)
            port = self._host.port
            host = self._host.local_address
            self._use_local()
            self._remote_token = token
            self._last_link = format_link(code, token, host, port)
            return code
        raise RuntimeError("No se pudo generar código único")

    def link_for_host(self, host: str) -> str:
        parsed = parse_link(self._last_link)
        if not parsed:
            return ""
        return format_link(parsed.code, parsed.token, host.strip(), parsed.port)

    def resolve_join_target(self, raw: str) -> tuple[str, ParsedLink | None, str | None]:
        """Devuelve (modo, parsed_link|None, error). modos: link, lan, invalid."""
        text = raw.strip()
        if not text:
            return "invalid", None, "Enlace vacío"

        parsed = parse_link(text)
        if parsed:
            self._use_remote(parsed.host, parsed.port, parsed.token)
            return "link", parsed, None

        if is_code_only(text):
            info = find_session(text, timeout=4.0)
            if info:
                self._use_remote(info["host"], int(info["port"]), info["token"])
                return "lan", ParsedLink(text, info["token"], info["host"], int(info["port"])), None
            return "lan", None, "Código no encontrado en la red local. Pega el enlace PG completo."

        return "invalid", None, "Formato inválido. Usa PG-123456-xxxxxxxx-IP:PUERTO"

    def join_room(self, code: str, joiner: str) -> dict[str, Any] | None:
        room = self.get_room(code)
        if not room:
            return None
        patch: dict[str, Any] = {"linked": True, f"{joiner}_joined_at": time.time()}
        if joiner == "admin":
            patch["admin_connected"] = True
            patch["disconnect_by_admin"] = False
        requests.patch(self._url(code), json=patch, headers=self._headers(), timeout=12)
        return self.get_room(code)

    def get_room(self, code: str) -> dict[str, Any] | None:
        try:
            response = requests.get(self._url(code), headers=self._headers(), timeout=12)
        except requests.RequestException:
            logger.exception("Error leyendo sala %s", code)
            return None
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None

    def patch_room(self, code: str, payload: dict[str, Any]) -> None:
        requests.patch(self._url(code), json=payload, headers=self._headers(), timeout=12)

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

    def connect_to_saved(self, code: str, link_host: str, link_token: str) -> bool:
        with self._host.lock:
            if code in self._host.rooms:
                self._use_local()
                self._remote_token = link_token
                return True
        if link_host and ":" in link_host:
            host, _, port_str = link_host.partition(":")
            try:
                port = int(port_str)
            except ValueError:
                return False
            self._use_remote(host, port, link_token)
            return bool(self.get_room(code))
        self._use_local()
        self._remote_token = link_token
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


# Alias para compatibilidad
PairingService = LinkService
