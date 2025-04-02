import logging
import httpx
from typing import Dict, Any, Optional

from app.config import settings
from app.services.messaging.interfaces import MessagingTransport, MessageContent, TextMessageContent, TemplateMessageContent, ImageMessageContent

logger = logging.getLogger(__name__)

class WhatsAppTransport(MessagingTransport):
    """Implementation of MessagingTransport for WhatsApp Business API."""
    
    def __init__(self):
        """Initialize WhatsApp transport with API configuration from settings."""
        self.api_url = settings.whatsapp_api_url
        self.api_key = settings.whatsapp_api_key
        self.verify_token = settings.whatsapp_verify_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.template_language_code = settings.whatsapp_template_language_code
    
    async def send_message(self, to: str, content: MessageContent) -> bool:
        """
        Send a message via WhatsApp.
        
        Args:
            to: Recipient's phone number in E.164 format
            content: Message content to send
            
        Returns:
            True if successful, False otherwise
        """
        # Clean the phone number
        to = to.strip()
        if not to.startswith("+"):
            to = "+" + to
            
        # Build the request payload based on message content type
        if isinstance(content, TextMessageContent):
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "body": content.text
                }
            }
        elif isinstance(content, TemplateMessageContent):
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": {
                    "name": content.template_name,
                    "language": {
                        "code": self.template_language_code
                    }
                }
            }
            
            # Add template data if provided
            if content.template_data:
                # WhatsApp expects components in a specific format
                # We'll keep the behavior aligned with the original implementation
                payload["template"]["components"] = []
                
                # Add parameters if available in the template data
                if "header" in content.template_data:
                    payload["template"]["components"].append({
                        "type": "header",
                        "parameters": [{"type": "text", "text": content.template_data["header"]}]
                    })
                
                if "body" in content.template_data and isinstance(content.template_data["body"], list):
                    body_params = []
                    for param in content.template_data["body"]:
                        body_params.append({"type": "text", "text": param})
                    
                    if body_params:
                        payload["template"]["components"].append({
                            "type": "body",
                            "parameters": body_params
                        })
                
                if "buttons" in content.template_data and isinstance(content.template_data["buttons"], list):
                    button_params = []
                    for btn in content.template_data["buttons"]:
                        button_params.append({"type": "text", "text": btn})
                    
                    if button_params:
                        payload["template"]["components"].append({
                            "type": "button",
                            "sub_type": "quick_reply",
                            "index": "0",
                            "parameters": button_params
                        })
                        
        elif isinstance(content, ImageMessageContent):
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "image",
                "image": {
                    "link": content.url
                }
            }
            
            if content.caption:
                payload["image"]["caption"] = content.caption
        else:
            logger.error(f"Unsupported message content type: {type(content)}")
            return False
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        api_url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
                logger.info(f"Message sent to {to} via WhatsApp")
                return True
                
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
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
                "platform": "whatsapp",
                "phone_number": from_data,
                "sender_id": from_data,  # WhatsApp uses phone number as sender ID
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
            
            logger.info(f"Successfully parsed WhatsApp message from {result['phone_number']}: {result['message'][:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing WhatsApp webhook: {e}", exc_info=True)
            return None