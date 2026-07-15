from aiogram import Router

from .start import router as start_router
from .portfolio import router as portfolio_router
from .common import router as common_router


def get_root_router() -> Router:
    root = Router()
    root.include_router(start_router)
    root.include_router(portfolio_router)
    root.include_router(common_router)
    return root
