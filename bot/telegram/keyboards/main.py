from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


DASHBOARD = "📊 Дашборд"
ACCOUNTS = "📋 Мои аккаунты"
ORDERS = "📦 Активные заказы"
HISTORY = "📜 История заказов"
SETTINGS = "⚙️ Настройки"
SEARCH = "🔍 Поиск"
STATS = "/stats"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=DASHBOARD), KeyboardButton(text=ACCOUNTS)],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=HISTORY)],
            [KeyboardButton(text=SETTINGS), KeyboardButton(text=SEARCH)],
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
    builder.button(text="✏️ Редактировать", callback_data=f"account:edit:{account_id}")
    builder.button(text="🗑 Удалить", callback_data=f"account:delete:{account_id}")
    builder.button(text="⬅️ К списку", callback_data="account:list")
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
    builder.adjust(1)
    return builder.as_markup()