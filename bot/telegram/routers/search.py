from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Account, Order
from bot.telegram.keyboards.main import SEARCH, main_menu

router = Router()


@router.message(Command("search"))
@router.message(F.text == SEARCH)
async def search_hint(message: Message) -> None:
    await message.answer("Используй /find <текст> для поиска по заказам и аккаунтам.")
    await message.answer("Главное меню", reply_markup=main_menu())


@router.message(Command("find"))
async def global_search(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    if not message.text:
        await message.answer("Используй /find <текст>.", reply_markup=main_menu())
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Используй /find <текст>.", reply_markup=main_menu())
        return
    text = parts[1].strip()
    async with session_factory() as session:
        accounts = (
            await session.scalars(
                select(Account)
                .where(or_(Account.title.ilike(f"%{text}%"), Account.steam_login.ilike(f"%{text}%")))
                .limit(5)
            )
        ).all()
        orders = (
            await session.scalars(
                select(Order)
                .where(or_(Order.funpay_order_id.ilike(f"%{text}%"), Order.buyer_nickname.ilike(f"%{text}%")))
                .limit(5)
            )
        ).all()
    if not accounts and not orders:
        await message.answer("Ничего не найдено.", reply_markup=main_menu())
        return
    lines = ["🔍 Результаты поиска"]
    for account in accounts:
        lines.append(f"Аккаунт: {account.title} / {account.steam_login} / {account.status.value}")
    for order in orders:
        lines.append(f"Заказ: {order.funpay_order_id} / {order.buyer_nickname} / {order.status.value}")
    await message.answer("\n".join(lines), reply_markup=main_menu())
