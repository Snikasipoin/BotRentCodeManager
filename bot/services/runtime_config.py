from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.app_config import BotSetting


@dataclass(frozen=True)
class RuntimeConfigDefaults:
    funpay_photo_request_text: str = "Аккаунты сдаются только для ПК клубов! Отправь фото подтверждения (как в примере ниже)."
    funpay_review_reminder_text: str = "Не забудь подтвердить сделку и оставить отзыв ⭐️"
    funpay_warning_text: str = "Внимание! Аренда заканчивается через {minutes} минут!"
    funpay_finish_text: str = "Время аренды закончилось. Спасибо за заказ."
    funpay_code_triggers: str = "код,guard,steam guard,faceit код,faceit,steam"


DEFAULTS: Final[RuntimeConfigDefaults] = RuntimeConfigDefaults()


class RuntimeConfigService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def ensure_defaults(self) -> None:
        async with self.session_factory() as session:
            for key, value in DEFAULTS.__dict__.items():
                existing = await session.get(BotSetting, key)
                if not existing:
                    session.add(BotSetting(key=key, value=value))
            await session.commit()

    async def get(self, key: str, default: str = "") -> str:
        async with self.session_factory() as session:
            setting = await session.get(BotSetting, key)
            return setting.value if setting else default

    async def set(self, key: str, value: str) -> None:
        async with self.session_factory() as session:
            setting = await session.get(BotSetting, key)
            if setting:
                setting.value = value
            else:
                session.add(BotSetting(key=key, value=value))
            await session.commit()

    async def get_text(self, key: str) -> str:
        return await self.get(key, getattr(DEFAULTS, key))

    async def get_code_triggers(self) -> list[str]:
        raw = await self.get_text("funpay_code_triggers")
        return [item.strip().lower() for item in raw.split(",") if item.strip()]
