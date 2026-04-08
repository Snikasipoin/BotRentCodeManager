from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


DASHBOARD = "Дашборд"
ACCOUNTS = "Мои аккаунты"
ORDERS = "Активные заказы"
HISTORY = "История заказов"
SETTINGS = "Настройки"
MESSAGES = "Сообщения"
SEARCH = "Поиск"
STATS = "/stats"


ACCOUNT_EDIT_FIELDS = (
    ("title", "Название"),
    ("steam_login", "Steam login"),
    ("steam_password", "Steam пароль"),
    ("faceit_login", "Faceit login"),
    ("faceit_password", "Faceit пароль"),
    ("email", "Email"),
    ("email_password", "Email пароль"),
    ("email_imap_host", "IMAP host"),
    ("email_imap_port", "IMAP port"),
    ("notes", "Заметки"),
)

AUTOMATION_FIELDS = (
    ("funpay_photo_request_text", "Запрос фото"),
    ("funpay_code_triggers", "Триггеры кода"),
    ("funpay_review_reminder_text", "Напоминание об отзыве"),
    ("funpay_warning_text", "Предупреждение о конце"),
    ("funpay_finish_text", "Сообщение о завершении"),
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=DASHBOARD), KeyboardButton(text=ACCOUNTS)],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=HISTORY)],
            [KeyboardButton(text=SETTINGS), KeyboardButton(text=MESSAGES)],
            [KeyboardButton(text=SEARCH)],
        ],
        resize_keyboard=True,
    )


def dashboard_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Обновить", callback_data="dashboard:refresh")
    builder.button(text="Статистика", callback_data="dashboard:stats")
    builder.adjust(2)
    return builder.as_markup()


def accounts_list_keyboard(items: list[tuple[int, str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for account_id, title, status in items:
        builder.button(text=f"{title} [{status}]", callback_data=f"account:view:{account_id}")
    builder.button(text="➕ Добавить аккаунт", callback_data="account:add")
    builder.adjust(1)
    return builder.as_markup()


def account_actions(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"account:editmenu:{account_id}")
    builder.button(text="🗑 Удалить", callback_data=f"account:delete:{account_id}")
    builder.button(text="⬅️ К списку", callback_data="account:list")
    builder.adjust(1)
    return builder.as_markup()


def account_edit_actions(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, label in ACCOUNT_EDIT_FIELDS:
        builder.button(text=label, callback_data=f"account:edit:{account_id}:{field}")
    builder.button(text="⬅️ К карточке", callback_data=f"account:view:{account_id}")
    builder.adjust(2)
    return builder.as_markup()


def automation_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, label in AUTOMATION_FIELDS:
        builder.button(text=label, callback_data=f"automation:edit:{field}")
    builder.button(text="⬅️ В настройки", callback_data="automation:back")
    builder.adjust(1)
    return builder.as_markup()


def dialogs_list_keyboard(items: list[tuple[int, str, str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chat_id, title, last_message, updated_at in items:
        builder.button(text=f"{title} | {last_message[:25]}", callback_data=f"dialog:view:{chat_id}")
    builder.button(text="⬅️ Главное меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def dialog_actions(chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Ответить", callback_data=f"dialog:reply:{chat_id}")
    builder.button(text="🔄 Обновить", callback_data=f"dialog:view:{chat_id}")
    builder.button(text="⬅️ К списку", callback_data="dialog:list")
    builder.adjust(1)
    return builder.as_markup()


def order_actions(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить (ПК-клуб)", callback_data=f"order:approve:{order_id}")
    builder.button(text="❌ Отклонить", callback_data=f"order:reject:{order_id}")
    builder.button(text="🎁 +30 минут", callback_data=f"order:bonus:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


def settings_actions() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Показать env-подсказку", callback_data="settings:env")
    builder.button(text="Проверить FunPay", callback_data="settings:funpay")
    builder.button(text="Автоответы FunPay", callback_data="settings:automation")
    builder.adjust(1)
    return builder.as_markup()
