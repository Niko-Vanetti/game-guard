"""Formato de enlace propio Program Guard (PG-Link)."""

from __future__ import annotations

import re
from dataclasses import dataclass

LINK_PREFIX = "PG"
LINK_PATTERN = re.compile(
    r"^PG[-:]?(?P<code>\d{6})[-:]?(?P<token>[A-Za-z0-9]{8})[-:@]?(?P<host>[^:\s]+):(?P<port>\d{1,5})$",
    re.IGNORECASE,
)
CODE_ONLY = re.compile(r"^\d{6}$")


@dataclass(frozen=True)
class ParsedLink:
    code: str
    token: str
    host: str
    port: int


def format_link(code: str, token: str, host: str, port: int) -> str:
    return f"{LINK_PREFIX}-{code}-{token}-{host}:{port}"


def parse_link(raw: str) -> ParsedLink | None:
    text = raw.strip()
    match = LINK_PATTERN.match(text)
    if not match:
        return None
    port = int(match.group("port"))
    if port < 1 or port > 65535:
        return None
    return ParsedLink(
        code=match.group("code"),
        token=match.group("token"),
        host=match.group("host"),
        port=port,
    )


def is_code_only(text: str) -> bool:
    return bool(CODE_ONLY.match(text.strip()))
