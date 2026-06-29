"""Detección de IP pública para enlaces entre redes distintas."""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

IP_ENDPOINTS = (
    "https://api.ipify.org?format=text",
    "https://ifconfig.me/ip",
)


def fetch_public_ip(timeout: float = 6.0) -> str | None:
    for url in IP_ENDPOINTS:
        try:
            response = requests.get(url, timeout=timeout)
        except requests.RequestException:
            logger.debug("No se pudo consultar %s", url)
            continue
        if response.status_code != 200:
            continue
        ip = response.text.strip()
        if ip and _looks_like_ip(ip):
            return ip
    return None


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False
