from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Account, Order
from bot.telegram.keyboards.main import SEARCH

router = Router()


@router.message(F.text == SEARCH)
async def search_hint(message: Message) -> None:
    await message.answer("Отправь текст для поиска по заказам или аккаунтам.")


@router.message(F.text.len() >= 3)
async def global_search(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    text = message.text.strip()
    if text.startswith("/"):
        return
    async with session_factory() as session:
        accounts = (await session.scalars(select(Account).where(or_(Account.title.ilike(f"%{text}%"), Account.steam_login.ilike(f"%{text}%"))).limit(5))).all()
        orders = (await session.scalars(select(Order).where(or_(Order.funpay_order_id.ilike(f"%{text}%"), Order.buyer_nickname.ilike(f"%{text}%"))).limit(5))).all()
    if not accounts and not orders:
        return
    lines = ["🔍 Результаты поиска"]
    for account in accounts:
        lines.append(f"Аккаунт: {account.title} / {account.steam_login} / {account.status.value}")
    for order in orders:
        lines.append(f"Заказ: {order.funpay_order_id} / {order.buyer_nickname} / {order.status.value}")
    await message.answer("\n".join(lines))