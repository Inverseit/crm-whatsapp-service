from fastapi import APIRouter
from .webhooks import router as webhooks_router
from .bookings import router as bookings_router
from .conversations import router as conversations_router

router = APIRouter()
router.include_router(webhooks_router)
router.include_router(bookings_router)
router.include_router(conversations_router)

__all__ = ["router"]