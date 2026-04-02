from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.db import engine
from app.handlers.common import router as common_router
from app.handlers.mailboxes import router as mailbox_router
from app.models import Base
from app.services.poller import MailPoller


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


async def on_startup(bot: Bot, poller: MailPoller) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await poller.start()
    logging.getLogger(__name__).info("Bot and poller started")


async def on_shutdown(poller: MailPoller) -> None:
    await poller.stop()
    await engine.dispose()


async def main() -> None:
    settings = get_settings()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    poller = MailPoller(bot=bot, interval_seconds=settings.poll_interval_seconds)

    dp.include_router(common_router)
    dp.include_router(mailbox_router)

    dp.startup.register(lambda _: on_startup(bot, poller))
    dp.shutdown.register(lambda _: on_shutdown(poller))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
