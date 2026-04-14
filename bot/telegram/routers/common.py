from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from bot.services.stats import StatsService
from bot.telegram.keyboards.main import ACCOUNTS, DASHBOARD, HISTORY, MESSAGES, ORDERS, SEARCH, SETTINGS, dashboard_actions, main_menu

router = Router()


async def render_dashboard(session_factory: async_sessionmaker[AsyncSession], stats_service: StatsService) -> str:
    async with session_factory() as session:
        stats = await stats_service.dashboard(session)
    return (
        "📊 Дашборд\n\n"
        f"Активные аренды: {stats['active_orders']}\n"
        f"Свободные аккаунты: {stats['available_accounts']}\n"
        f"Занятые аккаунты: {stats['rented_accounts']}\n"
        f"Всего заказов: {stats['total_orders']}"
    )


@router.message(Command("start"))
@router.message(Command("dashboard"))
@router.message(F.text == DASHBOARD)
async def cmd_start(message: Message, session_factory: async_sessionmaker[AsyncSession], stats_service: StatsService) -> None:
    text = await render_dashboard(session_factory, stats_service)
    await message.answer(text, reply_markup=dashboard_actions())


@router.message(Command("stats"))
async def cmd_stats(message: Message, session_factory: async_sessionmaker[AsyncSession], stats_service: StatsService) -> None:
    async with session_factory() as session:
        day = await stats_service.period_stats(session, 1)
        week = await stats_service.period_stats(session, 7)
        month = await stats_service.period_stats(session, 30)
    await message.answer(
        "📈 Статистика\n\n"
        f"За 1 день: заказов {day['orders']}, завершено {day['completed']}, отменено {day['cancelled']}\n"
        f"За 7 дней: заказов {week['orders']}, завершено {week['completed']}, отменено {week['cancelled']}\n"
        f"За 30 дней: заказов {month['orders']}, завершено {month['completed']}, отменено {month['cancelled']}",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "dashboard:refresh")
async def refresh_dashboard(callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession], stats_service: StatsService) -> None:
    await callback.answer("Обновлено")
    await callback.message.answer(await render_dashboard(session_factory, stats_service), reply_markup=dashboard_actions())


@router.callback_query(F.data == "dashboard:stats")
async def dashboard_stats(callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession], stats_service: StatsService) -> None:
    await callback.answer("Собираю статистику...")
    async with session_factory() as session:
        day = await stats_service.period_stats(session, 1)
        week = await stats_service.period_stats(session, 7)
        month = await stats_service.period_stats(session, 30)
    text = (
        "📈 Статистика\n\n"
        f"За 1 день: заказов {day['orders']}, завершено {day['completed']}, отменено {day['cancelled']}\n"
        f"За 7 дней: заказов {week['orders']}, завершено {week['completed']}, отменено {week['cancelled']}\n"
        f"За 30 дней: заказов {month['orders']}, завершено {month['completed']}, отменено {month['cancelled']}"
    )
    await callback.message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Главное меню", reply_markup=main_menu())


@router.message(F.text.in_({ACCOUNTS, ORDERS, HISTORY, SETTINGS, MESSAGES, SEARCH}))
async def section_redirect(message: Message) -> None:
    await message.answer("Открой нужный раздел соответствующей кнопкой или командой.", reply_markup=main_menu())




