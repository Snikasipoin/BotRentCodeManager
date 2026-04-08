from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.enums import OrderStatus
from bot.db.models import Order
from bot.services.order_processor import OrderProcessor
from bot.telegram.keyboards.main import ORDERS, main_menu, order_actions
from bot.utils.helpers import fmt_dt, fmt_timedelta_minutes

router = Router()


async def _active_orders_text(session: AsyncSession) -> tuple[str, list[Order]]:
    orders = (
        await session.scalars(
            select(Order)
            .where(Order.status.in_([OrderStatus.PENDING_PHOTO, OrderStatus.ACTIVE, OrderStatus.CREDS_SENT]))
            .order_by(Order.id.desc())
        )
    ).all()
    if not orders:
        return "Активных заказов нет.", []
    lines = [
        f"#{order.id} | {order.funpay_order_id} | {order.buyer_nickname} | {order.status.value} | до {fmt_dt(order.end_time)}"
        for order in orders
    ]
    return "📦 Активные заказы\n\n" + "\n".join(lines), orders


@router.message(Command("orders"))
@router.message(F.text == ORDERS)
async def orders_menu(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        text, orders = await _active_orders_text(session)
    await message.answer(text)
    for order in orders[:10]:
        await message.answer(
            f"Заказ {order.funpay_order_id}\nПокупатель: {order.buyer_nickname}\nСрок: {fmt_timedelta_minutes(order.rental_minutes)}\nСтатус: {order.status.value}",
            reply_markup=order_actions(order.id),
        )
    await message.answer("Главное меню", reply_markup=main_menu())


@router.callback_query(F.data.startswith("order:approve:"))
async def order_approve(callback: CallbackQuery, order_processor: OrderProcessor) -> None:
    order_id = int(callback.data.split(":")[-1])
    await order_processor.approve_photo(order_id)
    await callback.answer("Заказ подтверждён")
    await callback.message.answer(f"Заказ #{order_id} подтверждён и данные отправлены покупателю.")


@router.callback_query(F.data.startswith("order:reject:"))
async def order_reject(callback: CallbackQuery, order_processor: OrderProcessor) -> None:
    order_id = int(callback.data.split(":")[-1])
    await order_processor.reject_photo(order_id)
    await callback.answer("Фото отклонено")
    await callback.message.answer(f"Заказ #{order_id} отклонён.")


@router.callback_query(F.data.startswith("order:bonus:"))
async def order_bonus(callback: CallbackQuery, order_processor: OrderProcessor) -> None:
    order_id = int(callback.data.split(":")[-1])
    await order_processor.grant_review_bonus(order_id)
    await callback.answer("Бонус добавлен")
    await callback.message.answer(f"К заказу #{order_id} добавлено бонусное время.")
