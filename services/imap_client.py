from __future__ import annotations

import asyncio
import email
import imaplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message


@dataclass(slots=True)
class MailMessage:
    uid: int
    subject: str
    body: str
    received_at: datetime


class OutlookImapClient:
    async def fetch_recent_messages(self, email_address: str, password: str, imap_host: str, imap_port: int, last_seen_uid: int | None, max_messages: int = 20) -> tuple[list[MailMessage], int | None]:
        return await asyncio.to_thread(self._fetch_recent_messages_sync, email_address, password, imap_host, imap_port, last_seen_uid, max_messages)

    def _fetch_recent_messages_sync(self, email_address: str, password: str, imap_host: str, imap_port: int, last_seen_uid: int | None, max_messages: int) -> tuple[list[MailMessage], int | None]:
        client = imaplib.IMAP4_SSL(imap_host, imap_port)
        client.login(email_address, password)
        client.select("INBOX")

        status, data = client.uid("search", None, "ALL")
        if status != "OK" or not data or not data[0]:
            client.logout()
            return [], last_seen_uid

        all_uids = [int(item) for item in data[0].split()]
        newest_uid = all_uids[-1]

        if last_seen_uid is None:
            target_uids = all_uids[-max_messages:]
        else:
            target_uids = [uid for uid in all_uids if uid > last_seen_uid][-max_messages:]

        messages: list[MailMessage] = []

        for uid in target_uids:
            fetch_status, raw_data = client.uid("fetch", str(uid), "(RFC822)")
            if fetch_status != "OK" or not raw_data:
                continue

            raw_email = None
            for part in raw_data:
                if isinstance(part, tuple):
                    raw_email = part[1]
                    break

            if not raw_email:
                continue

            parsed = email.message_from_bytes(raw_email)
            messages.append(
                MailMessage(
                    uid=uid,
                    subject=self._decode_header_value(parsed.get("Subject", "")),
                    body=self._extract_text_body(parsed),
                    received_at=self._extract_received_at(parsed),
                )
            )

        client.logout()
        return messages, newest_uid

    def _decode_header_value(self, value: str) -> str:
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    def _extract_received_at(self, message: Message) -> datetime:
        header_value = message.get("Date")
        if not header_value:
            return datetime.now(timezone.utc)
        try:
            parsed_dt = email.utils.parsedate_to_datetime(header_value)
        except Exception:
            return datetime.now(timezone.utc)
        if parsed_dt.tzinfo is None:
            return parsed_dt.replace(tzinfo=timezone.utc)
        return parsed_dt.astimezone(timezone.utc)

    def _extract_text_body(self, message: Message) -> str:
        if message.is_multipart():
            parts: list[str] = []
            for part in message.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get_content_disposition() == "attachment":
                    continue
                if part.get_content_type() not in {"text/plain", "text/html"}:
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                try:
                    parts.append(payload.decode(charset, errors="ignore"))
                except LookupError:
                    parts.append(payload.decode("utf-8", errors="ignore"))
            return "\n".join(parts)

        payload = message.get_payload(decode=True)
        if not payload:
            return ""
        charset = message.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="ignore")
        except LookupError:
            return payload.decode("utf-8", errors="ignore")
