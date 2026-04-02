from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


STEAM_PATTERNS = [re.compile(r"\b([A-Z0-9]{5})\b")]
FACEIT_PATTERNS = [re.compile(r"\b(\d{4,8})\b")]


@dataclass(slots=True)
class ParsedCode:
    provider: str
    code: str
    subject: str
    received_at: datetime


def parse_security_code(subject: str, body: str, received_at: datetime | None = None) -> ParsedCode | None:
    content = f"{subject}\n{body}"
    lowered = content.lower()
    dt_value = received_at or datetime.now(timezone.utc)

    if "steam" in lowered and "guard" in lowered:
        for pattern in STEAM_PATTERNS:
            match = pattern.search(content)
            if match:
                return ParsedCode(provider="steam", code=match.group(1), subject=subject.strip()[:255], received_at=dt_value)

    if "faceit" in lowered:
        for pattern in FACEIT_PATTERNS:
            match = pattern.search(content)
            if match:
                return ParsedCode(provider="faceit", code=match.group(1), subject=subject.strip()[:255], received_at=dt_value)

    return None
