from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.config import get_settings
from bot.db.base import Base
from bot.db.session import get_engine, get_session_factory
from bot.funpay.client import FunPayClient
from bot.funpay.handlers import FunPayEventHandler
from bot.middlewares.admin import AdminOnlyMiddleware
from bot.services.order_processor import OrderProcessor
from bot.services.runtime_config import RuntimeConfigService
from bot.services.scheduler import SchedulerService
from bot.services.stats import StatsService
from bot.telegram.routers import setup_routers
from bot.utils.logging import setup_logging


async def create_schema() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    await create_schema()

    storage = MemoryStorage()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    root_router = setup_routers()
    root_router.message.middleware(AdminOnlyMiddleware())
    root_router.callback_query.middleware(AdminOnlyMiddleware())
    dp.include_router(root_router)

    session_factory: async_sessionmaker = get_session_factory()
    config_service = RuntimeConfigService(session_factory)
    await config_service.ensure_defaults()

    scheduler = SchedulerService()
    scheduler.start()
    stats_service = StatsService()
    funpay_client = FunPayClient()
    order_processor = OrderProcessor(session_factory, scheduler, bot, funpay_client, config_service)
    funpay_handler = FunPayEventHandler(funpay_client, order_processor, config_service)

    await funpay_client.start()
    await order_processor.restore_schedules()
    funpay_task = asyncio.create_task(funpay_handler.start(), name="funpay-events")

    logger.info("Bot started")
    try:
        await dp.start_polling(
            bot,
            session_factory=session_factory,
            stats_service=stats_service,
            order_processor=order_processor,
            funpay_client=funpay_client,
            config_service=config_service,
        )
    finally:
        funpay_task.cancel()
        await funpay_client.stop()
        await scheduler.shutdown()
        await storage.close()
        await bot.session.close()
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
