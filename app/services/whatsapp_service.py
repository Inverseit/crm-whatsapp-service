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
            # Use default config from settings
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
            "Authorization": f"Bearer {self.config.api_key}"
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
            logger.debug(f"Parsing webhook data: {data}")
            
            # Extract the message data from the webhook payload
            entry = data.get("entry", [])
            if not entry or not isinstance(entry, list) or len(entry) == 0:
                logger.debug("No entry field in webhook")
                return None
                
            changes = entry[0].get("changes", [])
            if not changes or not isinstance(changes, list) or len(changes) == 0:
                logger.debug("No changes field in entry")
                return None
                
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages or not isinstance(messages, list) or len(messages) == 0:
                logger.debug("No messages field in value")
                return None
                
            message = messages[0]
            message_type = message.get("type", "")
            
            # Extract sender information
            from_data = message.get("from", "")
            if not from_data:
                logger.debug("No from field in message")
                return None
                
            result = {
                "phone_number": from_data,
                "timestamp": message.get("timestamp", ""),
                "message_type": message_type,
                "message": ""  # Default empty message
            }
            
            # Extract message content based on type
            if message_type == "text":
                text_obj = message.get("text", {})
                if isinstance(text_obj, dict):
                    result["message"] = text_obj.get("body", "")
                else:
                    result["message"] = "[Text parsing error]"
            elif message_type == "image":
                result["message"] = "[Image received]"
                image_obj = message.get("image", {})
                if isinstance(image_obj, dict):
                    result["media_id"] = image_obj.get("id", "")
            elif message_type == "document":
                result["message"] = "[Document received]"
                doc_obj = message.get("document", {})
                if isinstance(doc_obj, dict):
                    result["media_id"] = doc_obj.get("id", "")
            elif message_type == "location":
                result["message"] = "[Location received]"
                location_obj = message.get("location", {})
                if isinstance(location_obj, dict):
                    result["latitude"] = location_obj.get("latitude")
                    result["longitude"] = location_obj.get("longitude")
            else:
                result["message"] = f"[{message_type} received]"
            
            logger.info(f"Successfully parsed message from {result['phone_number']}: {result['message'][:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing WhatsApp webhook: {e}", exc_info=True)
            return None