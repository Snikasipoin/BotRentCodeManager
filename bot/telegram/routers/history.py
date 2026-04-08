from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from bot.db.models import Order
from bot.telegram.keyboards.main import HISTORY, main_menu
from bot.utils.helpers import fmt_dt

router = Router()


@router.message(Command("history"))
@router.message(F.text == HISTORY)
async def history_menu(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        orders = (await session.scalars(select(Order).order_by(Order.id.desc()).limit(20))).all()
    if not orders:
        await message.answer("История заказов пока пуста.", reply_markup=main_menu())
        return
    lines = [f"#{order.id} | {order.funpay_order_id} | {order.status.value} | {fmt_dt(order.created_at)}" for order in orders]
    await message.answer("📜 Последние заказы\n\n" + "\n".join(lines), reply_markup=main_menu())
