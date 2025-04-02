import logging
from typing import Dict, Optional

from app.services.messaging.interfaces import MessagingTransport
from app.services.messaging.whatsapp import WhatsAppTransport
from app.services.messaging.telegramm import TelegramTransport

logger = logging.getLogger(__name__)

class MessagingFactory:
    """Factory for creating messaging transport instances."""
    
    _instances: Dict[str, MessagingTransport] = {}
    
    @classmethod
    def get_transport(cls, platform: str) -> Optional[MessagingTransport]:
        """
        Get a messaging transport for the specified platform.
        
        Args:
            platform: The messaging platform ("whatsapp", "telegram", etc.)
            
        Returns:
            A messaging transport instance or None if platform is not supported
        """
        platform = platform.lower()
        
        # Return cached instance if available
        if platform in cls._instances:
            return cls._instances[platform]
        
        # Create new instance
        transport = None
        
        if platform == "whatsapp":
            transport = WhatsAppTransport()
        elif platform == "telegram":
            transport = TelegramTransport()
        else:
            logger.error(f"Unsupported messaging platform: {platform}")
            return None
        
        # Cache and return the instance
        cls._instances[platform] = transport
        return transport
    
    @classmethod
    async def setup_webhooks(cls, base_url: str) -> Dict[str, bool]:
        """
        Set up webhooks for all messaging platforms.
        
        Args:
            base_url: The base URL of the application
            
        Returns:
            Dictionary of platform names and setup success status
        """
        results = {}
        
        # Set up Telegram webhook
        telegram = cls.get_transport("telegram")
        if telegram and hasattr(telegram, "set_webhook"):
            webhook_url = f"{base_url}/api/webhooks/telegram"
            results["telegram"] = await telegram.set_webhook(webhook_url)
        
        # WhatsApp webhooks are set up in the Meta dashboard, not programmatically
        
        return results