from aiogram import Router

from bot.telegram.routers.accounts import router as accounts_router
from bot.telegram.routers.common import router as common_router
from bot.telegram.routers.history import router as history_router
from bot.telegram.routers.orders import router as orders_router
from bot.telegram.routers.search import router as search_router
from bot.telegram.routers.settings import router as settings_router


def setup_routers() -> Router:
    router = Router()
    router.include_router(accounts_router)
    router.include_router(orders_router)
    router.include_router(history_router)
    router.include_router(settings_router)
    router.include_router(search_router)
    router.include_router(common_router)
    return router
