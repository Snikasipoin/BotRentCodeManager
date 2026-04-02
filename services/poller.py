from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from db import SessionLocal
from repositories import DeliveryRepository, MailboxRepository
from services.code_parser import parse_security_code
from services.imap_client import OutlookImapClient


logger = logging.getLogger(__name__)


class MailPoller:
    def __init__(self, bot: Bot, interval_seconds: int) -> None:
        self.bot = bot
        self.interval_seconds = interval_seconds
        self.imap_client = OutlookImapClient()
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="mail-poller")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                await self._poll_once()
            except Exception as exc:
                logger.exception("Poller cycle failed: %s", exc)

            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _poll_once(self) -> None:
        async with SessionLocal() as session:
            mailbox_repo = MailboxRepository(session)
            delivery_repo = DeliveryRepository(session)
            mailboxes = await mailbox_repo.list_active()

            for mailbox in mailboxes:
                try:
                    password = await mailbox_repo.decrypt_password(mailbox)
                    messages, newest_uid = await self.imap_client.fetch_recent_messages(
                        email_address=mailbox.email,
                        password=password,
                        imap_host=mailbox.imap_host,
                        imap_port=mailbox.imap_port,
                        last_seen_uid=mailbox.last_seen_uid,
                    )

                    for message in messages:
                        parsed = parse_security_code(subject=message.subject, body=message.body, received_at=message.received_at)
                        if not parsed:
                            continue

                        saved = await delivery_repo.create(
                            mailbox_id=mailbox.id,
                            message_uid=message.uid,
                            code=parsed.code,
                            code_type=parsed.provider,
                            message_subject=parsed.subject,
                            received_at=parsed.received_at,
                        )
                        if not saved:
                            continue

                        await self.bot.send_message(
                            mailbox.owner_telegram_id,
                            self._build_notification_text(
                                account_type=mailbox.account_type,
                                account_name=mailbox.account_name,
                                received_at=parsed.received_at,
                                code=parsed.code,
                            ),
                        )

                    await mailbox_repo.update_last_seen_uid(mailbox, newest_uid)
                except Exception as exc:
                    logger.exception("Mailbox processing failed for %s: %s", mailbox.email, exc)

    def _build_notification_text(self, account_type: str, account_name: str, received_at, code: str) -> str:
        local_time = received_at.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f'Вход в аккаунт "{account_type}"\n'
            f"Имя аккаунта: {account_name}\n"
            f"Время: {local_time}\n"
            f"Код: {code}"
        )
