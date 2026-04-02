from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Hosting panels sometimes start this file directly via `python main.py`.
# In that mode Python does not add the project root to `sys.path`, so
# absolute imports from the project root would fail.
if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from config import get_settings
from db import engine
from handlers.common import router as common_router
from handlers.mailboxes import router as mailbox_router
from models import Base
from services.poller import MailPoller


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

    async def startup_handler(**_: object) -> None:
        await on_startup(bot, poller)

    async def shutdown_handler(**_: object) -> None:
        await on_shutdown(poller)

    dp.startup.register(startup_handler)
    dp.shutdown.register(shutdown_handler)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
