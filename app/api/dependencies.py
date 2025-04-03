from typing import AsyncGenerator, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.gpt_service import GPTService
from app.services.booking_service import BookingManager
from app.services.platform_handler import PlatformHandler, get_platform_handler
from app.config import settings

# Create a singleton instance of GPTService
_gpt_service = GPTService(api_key=settings.openai_api_key, model=settings.openai_model)

async def get_gpt_service() -> GPTService:
    """
    Dependency for getting the GPT service.
    
    Returns:
        The GPT service instance
    """
    return _gpt_service

async def get_booking_manager(db: AsyncSession = Depends(get_db)) -> BookingManager:
    """
    Dependency for getting the booking manager with a database session.
    
    Args:
        db: The database session
        
    Returns:
        A new BookingManager instance with the provided db session
    """
    return BookingManager(db_session=db, gpt_service=_gpt_service)

async def get_platform_handler_factory(
    db: AsyncSession = Depends(get_db),
    gpt_service: GPTService = Depends(get_gpt_service)
) -> AsyncGenerator[function, None]:
    """
    Dependency for getting a factory function that creates platform handlers.
    
    Args:
        db: The database session
        gpt_service: The GPT service
        
    Returns:
        A factory function that creates platform handlers
    """
    def factory(platform: str) -> Optional[PlatformHandler]:
        """
        Get a platform handler for the specified platform.
        
        Args:
            platform: The platform name (telegram, whatsapp)
            
        Returns:
            A platform handler instance or None if platform is not supported
        """
        try:
            return get_platform_handler(platform.lower(), db, gpt_service)
        except ValueError:
            return None
            
    yield factory