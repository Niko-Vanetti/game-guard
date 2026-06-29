"""Servidor TCP en el Cliente — escucha solo en la red local."""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable
from typing import Any

from game_guard.config_manager import ConfigManager
from game_guard.monitor import ProcessMonitor
from game_guard.network.protocol import recv_message, send_message

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8741


class LocalCommandServer:
    def __init__(
        self,
        config: ConfigManager,
        monitor: ProcessMonitor,
        on_change: Callable[[], None] | None = None,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
    ) -> None:
        self.config = config
        self.monitor = monitor
        self.on_change = on_change
        self.host = host
        self.port = port
        self._running = False
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("Servidor local en puerto %s", self.port)

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _serve(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        self._sock.settimeout(1.0)

        while self._running:
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except TimeoutError:
                continue
            except OSError:
                if self._running:
                    logger.exception("Error aceptando conexión")
                break
            threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        logger.info("Conexión admin desde %s:%s", addr[0], addr[1])
        conn.settimeout(30.0)
        try:
            auth = recv_message(conn)
            if auth.get("type") != "auth":
                send_message(conn, {"type": "error", "message": "Se requiere autenticación"})
                return
            if auth.get("token") != self.config.pairing_token:
                send_message(conn, {"type": "error", "message": "Clave incorrecta"})
                return
            send_message(conn, {"type": "ok", "name": self.config.device_name})

            while self._running:
                try:
                    msg = recv_message(conn)
                except ConnectionError:
                    break
                response = self._process(msg)
                send_message(conn, response)
        except Exception:
            logger.exception("Error con cliente %s", addr)
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _process(self, msg: dict[str, Any]) -> dict[str, Any]:
        cmd = msg.get("type")

        if cmd == "get_status":
            return {
                "type": "status",
                "status": self.config.status_snapshot(),
                "config": self.config.to_remote_config(),
                "name": self.config.device_name,
                "device_id": self.config.device_id,
            }

        if cmd == "set_enabled":
            self.config.set_enabled(bool(msg.get("enabled", True)))
            self._notify()
            return {"type": "ok"}

        if cmd == "pause":
            self.config.pause_for_minutes(int(msg.get("minutes", 30)))
            self._notify()
            return {"type": "ok"}

        if cmd == "clear_pause":
            self.config.clear_pause()
            self._notify()
            return {"type": "ok"}

        if cmd == "kill_games":
            self.monitor.kill_blocked_now()
            return {"type": "ok"}

        if cmd == "update_config":
            remote_cfg = msg.get("config")
            if isinstance(remote_cfg, dict):
                self.config.apply_remote_config(remote_cfg)
                self._notify()
            return {"type": "ok"}

        return {"type": "error", "message": f"Comando desconocido: {cmd}"}

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
