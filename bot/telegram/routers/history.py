from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Order
from bot.telegram.keyboards.main import HISTORY
from bot.utils.helpers import fmt_dt

router = Router()


@router.message(F.text == HISTORY)
async def history_menu(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        orders = (await session.scalars(select(Order).order_by(Order.id.desc()).limit(20))).all()
    if not orders:
        await message.answer("История заказов пока пуста.")
        return
    lines = [f"#{order.id} | {order.funpay_order_id} | {order.status.value} | {fmt_dt(order.created_at)}" for order in orders]
    await message.answer("📜 Последние заказы\n\n" + "\n".join(lines))