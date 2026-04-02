from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models import Mailbox


ADD_MAIL_LABEL = "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u0447\u0442\u0443"
LIST_MAIL_LABEL = "\u041c\u043e\u0438 \u043f\u043e\u0447\u0442\u044b"
HOME_LABEL = "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e"
BACK_TO_LIST_LABEL = "\u041a \u0441\u043f\u0438\u0441\u043a\u0443 \u043f\u043e\u0447\u0442"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_MAIL_LABEL), KeyboardButton(text=LIST_MAIL_LABEL)],
            [KeyboardButton(text=HOME_LABEL)],
        ],
        resize_keyboard=True,
    )


def mailbox_list_keyboard(mailboxes: list[Mailbox]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mailbox in mailboxes:
        status = "ON" if mailbox.is_active else "OFF"
        builder.button(text=f"{mailbox.id}. {mailbox.title} [{status}]", callback_data=f"mailbox:{mailbox.id}")
    builder.button(text=HOME_LABEL, callback_data="nav:home")
    builder.adjust(1)
    return builder.as_markup()


def mailbox_actions_keyboard(mailbox_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="\u0412\u043a\u043b/\u0412\u044b\u043a\u043b", callback_data=f"toggle:{mailbox_id}")
    builder.button(text="\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435", callback_data=f"edit_title:{mailbox_id}")
    builder.button(text="\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u0430\u043a\u043a\u0430\u0443\u043d\u0442", callback_data=f"edit_account:{mailbox_id}")
    builder.button(text="\u0418\u0437\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u0430\u0440\u043e\u043b\u044c", callback_data=f"edit_password:{mailbox_id}")
    builder.button(text="\u0423\u0434\u0430\u043b\u0438\u0442\u044c", callback_data=f"delete:{mailbox_id}")
    builder.button(text=BACK_TO_LIST_LABEL, callback_data="nav:list")
    builder.button(text=HOME_LABEL, callback_data="nav:home")
    builder.adjust(1)
    return builder.as_markup()
