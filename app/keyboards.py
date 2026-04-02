from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models import Mailbox


def mailbox_list_keyboard(mailboxes: list[Mailbox]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mailbox in mailboxes:
        status = "ON" if mailbox.is_active else "OFF"
        builder.button(text=f"{mailbox.id}. {mailbox.title} [{status}]", callback_data=f"mailbox:{mailbox.id}")
    builder.adjust(1)
    return builder.as_markup()


def mailbox_actions_keyboard(mailbox_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Вкл/Выкл", callback_data=f"toggle:{mailbox_id}")
    builder.button(text="Изменить название", callback_data=f"edit_title:{mailbox_id}")
    builder.button(text="Изменить аккаунт", callback_data=f"edit_account:{mailbox_id}")
    builder.button(text="Изменить пароль", callback_data=f"edit_password:{mailbox_id}")
    builder.button(text="Удалить", callback_data=f"delete:{mailbox_id}")
    builder.adjust(1)
    return builder.as_markup()
