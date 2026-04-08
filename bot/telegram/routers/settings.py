from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.funpay.client import FunPayClient
from bot.telegram.keyboards.main import SETTINGS, settings_actions, main_menu

router = Router()


@router.message(F.text == SETTINGS)
async def settings_menu(message: Message) -> None:
    settings = get_settings()
    admins = ", ".join(str(admin_id) for admin_id in settings.admin_id)
    text = (
        "⚙️ Настройки\n\n"
        f"Админы: {admins}\n"
        f"База: {settings.database_url}\n"
        f"Интервал FunPay: {settings.funpay_poll_interval} сек.\n"
        f"Часовой пояс: {settings.timezone_name}"
    )
    await message.answer(text, reply_markup=settings_actions())
    await message.answer("Главное меню", reply_markup=main_menu())


@router.callback_query(F.data == "settings:env")
async def settings_env(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Проверь .env: BOT_TOKEN, ADMIN_ID (можно через запятую), DATABASE_URL, ENCRYPTION_KEY, FUNPAY_GOLDEN_KEY, FUNPAY_USER_AGENT, FUNPAY_POLL_INTERVAL, EMAIL_IMAP_TIMEOUT, REVIEW_BONUS_MINUTES, REMINDER_AFTER_MINUTES, EXPIRING_WARNING_MINUTES, TZ, LOG_LEVEL"
    )


@router.callback_query(F.data == "settings:funpay")
async def settings_funpay(callback: CallbackQuery, funpay_client: FunPayClient) -> None:
    await callback.answer()
    mode = "подключен" if funpay_client.account else "не инициализирован"
    await callback.message.answer(f"Состояние FunPay клиента: {mode}")
