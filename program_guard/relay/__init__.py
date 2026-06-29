# Compatibilidad — usar program_guard.link
from program_guard.link import LinkService, PairingService
from program_guard.link.service import LinkService as _LinkService

PairingService = _LinkService
load_relay_settings = lambda: {}
load_cloud_settings = load_relay_settings

__all__ = ["PairingService", "LinkService", "load_relay_settings", "load_cloud_settings"]
