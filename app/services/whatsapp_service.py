import logging
import httpx
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

class WhatsAppConfig(BaseModel):
    """WhatsApp API configuration."""
    api_url: str = Field(..., description="WhatsApp API URL")
    api_key: str = Field(..., description="WhatsApp API key")
    verify_token: str = Field(..., description="WhatsApp webhook verification token")
    phone_number_id: str = Field(..., description="WhatsApp phone number ID")

class WhatsAppService:
    """Service for sending messages via WhatsApp Business API."""
    
    def __init__(self, config: Optional[WhatsAppConfig] = None):
        """
        Initialize the WhatsApp service.
        
        Args:
            config: The WhatsApp API configuration
        """
        if config:
            self.config = config
        else:
            self.config = WhatsAppConfig(
                api_url=settings.whatsapp_api_url,
                api_key=settings.whatsapp_api_key,
                verify_token=settings.whatsapp_verify_token,
                phone_number_id=settings.whatsapp_phone_number_id
            )
    
    async def send_message(self, to: str, text: str) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.
        
        Args:
            to: The recipient's phone number in E.164 format
            text: The message text
            
        Returns:
            The API response
        """
        # Clean the phone number
        to = to.strip()
        if not to.startswith("+"):
            to = "+" + to
            
        # Build the request payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.access_token}"
        }
        
        api_url = f"{self.config.api_url}/{self.config.phone_number_id}/messages"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            raise
    
    async def parse_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook data from WhatsApp.
        
        Args:
            data: The webhook payload
            
        Returns:
            Parsed message information or None if not a valid message
        """
        try:
            # Extract the message data from the webhook payload
            entry = data.get("entry", [])
            if not entry:
                return None
                
            changes = entry[0].get("changes", [])
            if not changes:
                return None
                
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None
                
            message = messages[0]
            message_type = message.get("type")
            
            # Extract sender information
            from_data = message.get("from")
            if not from_data:
                return None
                
            result = {
                "phone_number": from_data,
                "timestamp": message.get("timestamp", ""),
                "message_type": message_type,
            }
            
            # Extract message content based on type
            if message_type == "text":
                text = message.get("text", {}).get("body", "")
                result["message"] = text
            elif message_type == "image":
                result["message"] = "[Image received]"
                result["media_id"] = message.get("image", {}).get("id", "")
            elif message_type == "document":
                result["message"] = "[Document received]"
                result["media_id"] = message.get("document", {}).get("id", "")
            elif message_type == "location":
                result["message"] = "[Location received]"
                location = message.get("location", {})
                result["latitude"] = location.get("latitude")
                result["longitude"] = location.get("longitude")
            else:
                result["message"] = f"[{message_type} received]"
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing WhatsApp webhook: {e}")
            return None