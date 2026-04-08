from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.dialogs import FunPayDialog, FunPayDialogMessage
from bot.db.models import Order
from bot.funpay.client import FunPayClient


class FunPayDialogService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], funpay_client: FunPayClient) -> None:
        self.session_factory = session_factory
        self.funpay_client = funpay_client

    async def ensure_dialog(self, chat_id: int, buyer_nickname: str | None = None, order: Order | None = None) -> FunPayDialog:
        async with self.session_factory() as session:
            dialog = await session.scalar(select(FunPayDialog).where(FunPayDialog.chat_id == chat_id))
            if not dialog:
                dialog = FunPayDialog(
                    chat_id=chat_id,
                    buyer_nickname=buyer_nickname,
                    current_order_id=order.id if order else None,
                    last_message_at=datetime.now(timezone.utc),
                )
                session.add(dialog)
                await session.flush()
            else:
                if buyer_nickname:
                    dialog.buyer_nickname = buyer_nickname
                if order:
                    dialog.current_order_id = order.id
            await session.commit()
            await session.refresh(dialog)
            return dialog

    async def record_incoming(self, chat_id: int, text: str, buyer_nickname: str | None = None, order: Order | None = None, has_photo: bool = False, photo_path: str | None = None) -> None:
        dialog = await self.ensure_dialog(chat_id, buyer_nickname=buyer_nickname, order=order)
        async with self.session_factory() as session:
            dialog = await session.get(FunPayDialog, dialog.id)
            if not dialog:
                return
            dialog.last_message_text = text
            dialog.last_message_at = datetime.now(timezone.utc)
            if buyer_nickname:
                dialog.buyer_nickname = buyer_nickname
            if order:
                dialog.current_order_id = order.id
            session.add(
                FunPayDialogMessage(
                    dialog_id=dialog.id,
                    direction="incoming",
                    text=text,
                    has_photo=has_photo,
                    photo_path=photo_path,
                )
            )
            await session.commit()

    async def record_outgoing(self, chat_id: int, text: str) -> None:
        dialog = await self.ensure_dialog(chat_id)
        async with self.session_factory() as session:
            dialog = await session.get(FunPayDialog, dialog.id)
            if not dialog:
                return
            dialog.last_message_text = text
            dialog.last_message_at = datetime.now(timezone.utc)
            session.add(
                FunPayDialogMessage(
                    dialog_id=dialog.id,
                    direction="outgoing",
                    text=text,
                    has_photo=False,
                )
            )
            await session.commit()

    async def list_recent_dialogs(self, limit: int = 10) -> list[FunPayDialog]:
        async with self.session_factory() as session:
            dialogs = (
                await session.scalars(select(FunPayDialog).order_by(desc(FunPayDialog.last_message_at), desc(FunPayDialog.updated_at)).limit(limit))
            ).all()
            return dialogs

    async def get_history(self, chat_id: int, limit: int = 20) -> list[FunPayDialogMessage]:
        async with self.session_factory() as session:
            dialog = await session.scalar(select(FunPayDialog).where(FunPayDialog.chat_id == chat_id))
            if not dialog:
                return []
            messages = (
                await session.scalars(
                    select(FunPayDialogMessage)
                    .where(FunPayDialogMessage.dialog_id == dialog.id)
                    .order_by(FunPayDialogMessage.created_at.desc())
                    .limit(limit)
                )
            ).all()
            return list(reversed(messages))

    async def get_dialog(self, chat_id: int) -> FunPayDialog | None:
        async with self.session_factory() as session:
            return await session.scalar(select(FunPayDialog).where(FunPayDialog.chat_id == chat_id))

    async def reply(self, chat_id: int, text: str) -> None:
        await self.funpay_client.send_text(chat_id, text)
        await self.record_outgoing(chat_id, text)
