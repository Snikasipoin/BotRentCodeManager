from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeDelivery, Mailbox
from app.security import SecretCipher


class MailboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cipher = SecretCipher()

    async def create_mailbox(self, owner_telegram_id: int, title: str, email: str, password: str, imap_host: str, imap_port: int, account_type: str, account_name: str) -> Mailbox:
        mailbox = Mailbox(
            owner_telegram_id=owner_telegram_id,
            title=title,
            email=email,
            encrypted_password=self.cipher.encrypt(password),
            imap_host=imap_host,
            imap_port=imap_port,
            account_type=account_type,
            account_name=account_name,
            is_active=True,
        )
        self.session.add(mailbox)
        await self.session.commit()
        await self.session.refresh(mailbox)
        return mailbox

    async def list_by_owner(self, owner_telegram_id: int) -> list[Mailbox]:
        result = await self.session.execute(select(Mailbox).where(Mailbox.owner_telegram_id == owner_telegram_id).order_by(Mailbox.id.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, mailbox_id: int) -> Mailbox | None:
        result = await self.session.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
        return result.scalar_one_or_none()

    async def get_by_id_for_owner(self, mailbox_id: int, owner_telegram_id: int) -> Mailbox | None:
        result = await self.session.execute(
            select(Mailbox).where(Mailbox.id == mailbox_id, Mailbox.owner_telegram_id == owner_telegram_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Mailbox]:
        result = await self.session.execute(select(Mailbox).where(Mailbox.is_active.is_(True)).order_by(Mailbox.id.asc()))
        return list(result.scalars().all())

    async def delete(self, mailbox: Mailbox) -> None:
        await self.session.delete(mailbox)
        await self.session.commit()

    async def toggle_active(self, mailbox: Mailbox) -> Mailbox:
        mailbox.is_active = not mailbox.is_active
        mailbox.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(mailbox)
        return mailbox

    async def update_title(self, mailbox: Mailbox, value: str) -> Mailbox:
        mailbox.title = value
        mailbox.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(mailbox)
        return mailbox

    async def update_account_name(self, mailbox: Mailbox, value: str) -> Mailbox:
        mailbox.account_name = value
        mailbox.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(mailbox)
        return mailbox

    async def update_password(self, mailbox: Mailbox, value: str) -> Mailbox:
        mailbox.encrypted_password = self.cipher.encrypt(value)
        mailbox.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(mailbox)
        return mailbox

    async def update_last_seen_uid(self, mailbox: Mailbox, last_seen_uid: int | None) -> None:
        mailbox.last_seen_uid = last_seen_uid
        mailbox.last_checked_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def decrypt_password(self, mailbox: Mailbox) -> str:
        return self.cipher.decrypt(mailbox.encrypted_password)


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, mailbox_id: int, message_uid: int, code: str, code_type: str, message_subject: str, received_at: datetime) -> bool:
        item = CodeDelivery(
            mailbox_id=mailbox_id,
            message_uid=message_uid,
            code=code,
            code_type=code_type,
            message_subject=message_subject,
            received_at=received_at,
        )
        self.session.add(item)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return False

        return True
