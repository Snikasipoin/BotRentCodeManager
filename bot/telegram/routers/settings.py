from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.funpay.client import FunPayClient
from bot.services.runtime_config import DEFAULTS, RuntimeConfigService
from bot.telegram.keyboards.main import SETTINGS, automation_actions, main_menu, settings_actions
from bot.telegram.states.account import AutomationForm

router = Router()


@router.message(Command("settings"))
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


async def _render_automation_text(config_service: RuntimeConfigService) -> str:
    photo = await config_service.get_text("funpay_photo_request_text")
    triggers = await config_service.get_text("funpay_code_triggers")
    reminder = await config_service.get_text("funpay_review_reminder_text")
    warning = await config_service.get_text("funpay_warning_text")
    finish = await config_service.get_text("funpay_finish_text")
    return (
        "🤖 Автоответы FunPay\n\n"
        f"Запрос фото:\n{photo}\n\n"
        f"Триггеры кода:\n{triggers}\n\n"
        f"Напоминание об отзыве:\n{reminder}\n\n"
        f"Предупреждение о конце:\n{warning}\n\n"
        f"Сообщение о завершении:\n{finish}"
    )


@router.callback_query(F.data == "settings:automation")
async def settings_automation(callback: CallbackQuery, config_service: RuntimeConfigService) -> None:
    await callback.answer()
    await callback.message.answer(await _render_automation_text(config_service), reply_markup=automation_actions())


@router.callback_query(F.data == "automation:back")
async def automation_back(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Вернуться в настройки", reply_markup=settings_actions())


@router.callback_query(F.data.startswith("automation:edit:"))
async def automation_edit(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":")[-1]
    await state.set_state(AutomationForm.value)
    await state.update_data(field=field)
    await callback.answer()
    prompts = {
        "funpay_photo_request_text": "Введи новый текст запроса фото",
        "funpay_code_triggers": "Введи триггеры через запятую",
        "funpay_review_reminder_text": "Введи новый текст напоминания об отзыве",
        "funpay_warning_text": "Введи новый текст предупреждения, можно использовать {minutes}",
        "funpay_finish_text": "Введи новый текст завершения аренды",
    }
    await callback.message.answer(prompts.get(field, "Введи новое значение"))


@router.message(AutomationForm.value)
async def automation_value(message: Message, state: FSMContext, config_service: RuntimeConfigService) -> None:
    data = await state.get_data()
    field = str(data["field"])
    value = message.text.strip()
    await config_service.set(field, value)
    await state.clear()
    await message.answer("Автоответ обновлён.", reply_markup=main_menu())
    await message.answer(await _render_automation_text(config_service), reply_markup=automation_actions())
