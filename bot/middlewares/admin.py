from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import get_settings


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        settings = get_settings()
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
        if user_id is None or not settings.is_admin(user_id):
            if isinstance(event, Message):
                await event.answer("Доступ запрещён")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещён", show_alert=True)
            return None
        return await handler(event, data)
