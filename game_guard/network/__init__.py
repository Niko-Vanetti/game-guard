"""Comunicación local Admin ↔ Cliente (sin servidor externo)."""

from game_guard.network.local_client import AdminConnection
from game_guard.network.local_server import LocalCommandServer
from game_guard.network.protocol import get_local_ip

__all__ = ["AdminConnection", "LocalCommandServer", "get_local_ip"]
