from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import get_settings


router = Router()


def is_allowed_user(user_id: int) -> bool:
    settings = get_settings()
    allowed = settings.owner_telegram_ids
    if not allowed:
        return True
    return user_id in allowed


async def ensure_access(message: Message) -> bool:
    if not message.from_user:
        await message.answer("Не удалось определить Telegram пользователя.")
        return False
    if not is_allowed_user(message.from_user.id):
        await message.answer("Доступ запрещен.")
        return False
    return True


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not await ensure_access(message):
        return
    text = (
        "Бот готов к работе.\n\n"
        "Команды:\n"
        "/add_mail - добавить почту\n"
        "/list_mail - список почт\n"
        "/help - помощь\n"
        "/cancel - отменить текущее действие"
    )
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not await ensure_access(message):
        return
    await message.answer(
        "Добавляй Outlook/Hotmail ящики, указывай тип аккаунта steam/faceit, а бот будет сам проверять письма и присылать код."
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.clear()
    await message.answer("Текущее действие отменено.")
