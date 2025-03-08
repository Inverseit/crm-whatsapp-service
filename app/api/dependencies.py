from typing import Generator

from app.services.gpt_service import GPTService
from app.services.booking_service import BookingManager
from app.services.whatsapp_service import WhatsAppService
from app.config import settings

# Create a singleton instance of WhatsAppService
_whatsapp_service = WhatsAppService()

# Create a singleton instance of GPTService
_gpt_service = GPTService(api_key=settings.openai_api_key, model=settings.openai_model)

# Create a singleton instance of BookingManager
_booking_manager = BookingManager(gpt_service=_gpt_service, whatsapp_service=_whatsapp_service)

def get_gpt_service() -> GPTService:
    """
    Dependency for getting the GPT service.
    
    Returns:
        The GPT service instance
    """
    return _gpt_service

def get_whatsapp_service() -> WhatsAppService:
    """
    Dependency for getting the WhatsApp service.
    
    Returns:
        The WhatsApp service instance
    """
    return _whatsapp_service

def get_booking_manager() -> BookingManager:
    """
    Dependency for getting the booking manager.
    
    Returns:
        The booking manager instance
    """
    return _booking_manager