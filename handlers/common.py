from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import get_settings
from keyboards import ADD_MAIL_LABEL, HOME_LABEL, LIST_MAIL_LABEL, main_menu_keyboard


router = Router()


MAIN_MENU_TEXT = (
    "Ѕот готов к работе.\n\n"
    "„то можно сделать:\n"
    f"Х {ADD_MAIL_LABEL} - добавить новый €щик\n"
    f"Х {LIST_MAIL_LABEL} - открыть список сохраненных почт\n"
    "/cancel - отменить текущее действие"
)


HELP_TEXT = (
    "ƒобавл€й Outlook/Hotmail €щики, а бот будет автоматически отслеживать письма Steam Guard и FACEIT.\n\n"
    "“ип письма вручную выбирать больше не нужно: бот сам определ€ет, что пришло."
)


def is_allowed_user(user_id: int) -> bool:
    settings = get_settings()
    allowed = settings.owner_telegram_ids
    if not allowed:
        return True
    return user_id in allowed


async def ensure_access(message: Message) -> bool:
    if not message.from_user:
        await message.answer("Ќе удалось определить Telegram пользовател€.", reply_markup=main_menu_keyboard())
        return False
    if not is_allowed_user(message.from_user.id):
        await message.answer("ƒоступ запрещен.", reply_markup=main_menu_keyboard())
        return False
    return True


async def send_main_menu(target: Message | CallbackQuery, text: str = MAIN_MENU_TEXT) -> None:
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=main_menu_keyboard())
    else:
        await target.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("start"))
@router.message(F.text == HOME_LABEL)
async def cmd_start(message: Message) -> None:
    if not await ensure_access(message):
        return
    await send_main_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not await ensure_access(message):
        return
    await message.answer(HELP_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.clear()
    await message.answer("“екущее действие отменено.", reply_markup=main_menu_keyboard())
