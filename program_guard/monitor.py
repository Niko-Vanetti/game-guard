"""Monitor de procesos bloqueados."""

from __future__ import annotations

import logging
import time
from typing import Callable

import psutil

from program_guard.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ProcessMonitor:
    def __init__(
        self,
        config: ConfigManager,
        on_block: Callable[[str], None] | None = None,
        interval: float = 2.0,
    ) -> None:
        self.config = config
        self.on_block = on_block
        self.interval = interval
        self._running = False
        self._recently_blocked: dict[str, float] = {}

    def start(self) -> None:
        self._running = True
        while self._running:
            self.interval = self.config.monitor_interval
            try:
                self._scan_once()
            except Exception:
                logger.exception("Error en monitor de procesos")
            time.sleep(self.interval)

    def stop(self) -> None:
        self._running = False

    def kill_blocked_now(self) -> None:
        blocked_names = {app["exe_name"] for app in self.config.get_blocked_apps()}
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in blocked_names:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def _scan_once(self) -> None:
        if not self.config.is_enabled or self.config.is_play_allowed_now():
            return
        blocked_names = {app["exe_name"] for app in self.config.get_blocked_apps()}
        if not blocked_names:
            return
        now = time.time()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name not in blocked_names:
                    continue
                if now - self._recently_blocked.get(name, 0) < 5:
                    continue
                proc.terminate()
                self._recently_blocked[name] = now
                if self.on_block:
                    self.on_block(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
