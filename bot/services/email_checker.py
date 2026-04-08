from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from imap_tools import AND, MailBox
from loguru import logger

from bot.config import get_settings
from bot.db.models import Account
from bot.utils.encryption import Cipher

STEAM_CODE_RE = re.compile(r"\b([A-Z0-9]{5})\b")
FACEIT_CODE_RE = re.compile(r"\b(\d{4,8})\b")


@dataclass(slots=True)
class MailCodeResult:
    provider: str
    code: str
    subject: str
    received_at: datetime


class EmailChecker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cipher = Cipher()

    async def fetch_latest_code(self, account: Account) -> MailCodeResult | None:
        password = self.cipher.decrypt(account.email_password_encrypted)
        if not password:
            return None
        return await asyncio.to_thread(
            self._fetch_latest_code_sync,
            account.email,
            password,
            account.email_imap_host,
            account.email_imap_port,
        )

    def _fetch_latest_code_sync(self, email: str, password: str, host: str, port: int) -> MailCodeResult | None:
        logger.debug("Checking mailbox for codes: {}", email)
        with MailBox(host, port=port).login(email, password) as mailbox:
            messages = mailbox.fetch(criteria=AND(all=True), reverse=True, limit=10)
            for message in messages:
                content = f"{message.subject}\n{message.text or ''}\n{message.html or ''}"
                lowered = content.lower()
                received_at = message.date.astimezone(timezone.utc) if message.date else datetime.now(timezone.utc)
                if "steam" in lowered and "guard" in lowered:
                    match = STEAM_CODE_RE.search(content)
                    if match:
                        return MailCodeResult("steam", match.group(1), message.subject or "Steam Guard", received_at)
                if "faceit" in lowered:
                    match = FACEIT_CODE_RE.search(content)
                    if match:
                        return MailCodeResult("faceit", match.group(1), message.subject or "FACEIT", received_at)
        return None