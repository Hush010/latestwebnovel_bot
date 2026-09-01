from aiogram import Dispatcher
from .common import router as common_router
from .novel import router as novel_router


def register_all_handlers(dp: Dispatcher):
    """Register all active modular handlers on the main dispatcher."""
    dp.include_router(common_router)
    dp.include_router(novel_router)
