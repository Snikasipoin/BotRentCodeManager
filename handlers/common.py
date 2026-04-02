from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import get_settings
from keyboards import ADD_MAIL_LABEL, HOME_LABEL, LIST_MAIL_LABEL, main_menu_keyboard


router = Router()


MAIN_MENU_TEXT = (
    "\u0411\u043e\u0442 \u0433\u043e\u0442\u043e\u0432 \u043a \u0440\u0430\u0431\u043e\u0442\u0435.\n\n"
    "\u0427\u0442\u043e \u043c\u043e\u0436\u043d\u043e \u0441\u0434\u0435\u043b\u0430\u0442\u044c:\n"
    f"- {ADD_MAIL_LABEL} - \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043d\u043e\u0432\u044b\u0439 \u044f\u0449\u0438\u043a\n"
    f"- {LIST_MAIL_LABEL} - \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043d\u044b\u0445 \u043f\u043e\u0447\u0442\n"
    "/cancel - \u043e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0442\u0435\u043a\u0443\u0449\u0435\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435"
)


HELP_TEXT = (
    "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0439 Outlook/Hotmail \u044f\u0449\u0438\u043a\u0438, \u0430 \u0431\u043e\u0442 \u0431\u0443\u0434\u0435\u0442 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u043f\u0438\u0441\u044c\u043c\u0430 Steam Guard \u0438 FACEIT.\n\n"
    "\u0422\u0438\u043f \u043f\u0438\u0441\u044c\u043c\u0430 \u0432\u0440\u0443\u0447\u043d\u0443\u044e \u0432\u044b\u0431\u0438\u0440\u0430\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0435 \u043d\u0443\u0436\u043d\u043e: \u0431\u043e\u0442 \u0441\u0430\u043c \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u0435\u0442, \u0447\u0442\u043e \u043f\u0440\u0438\u0448\u043b\u043e."
)


def is_allowed_user(user_id: int) -> bool:
    settings = get_settings()
    allowed = settings.owner_telegram_ids
    if not allowed:
        return True
    return user_id in allowed


async def ensure_access(message: Message) -> bool:
    if not message.from_user:
        await message.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c Telegram \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f.", reply_markup=main_menu_keyboard())
        return False
    if not is_allowed_user(message.from_user.id):
        await message.answer("\u0414\u043e\u0441\u0442\u0443\u043f \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d.", reply_markup=main_menu_keyboard())
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
    await message.answer("\u0422\u0435\u043a\u0443\u0449\u0435\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u043e.", reply_markup=main_menu_keyboard())
