import logging
from typing import Dict, Any, Optional, List
import json
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackContext
from telegram.constants import ParseMode
import asyncio

from app.config import settings
from app.services.messaging.interfaces import MessagingTransport, MessageContent, TextMessageContent, TemplateMessageContent, ImageMessageContent

logger = logging.getLogger(__name__)

class TelegramTransport(MessagingTransport):
    """Implementation of MessagingTransport for Telegram Bot API using python-telegram-bot library."""
    
    def __init__(self):
        """Initialize Telegram transport with API configuration from settings."""
        self.api_token = settings.telegram_api_token
        self.webhook_token = settings.telegram_webhook_token
        self._bot = None
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize the Telegram bot instance."""
        if not self.api_token:
            logger.error("Telegram API token not configured")
            return
            
        try:
            self._bot = Bot(token=self.api_token)
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_message(self, to: str, content: MessageContent) -> bool:
        """
        Send a message via Telegram.
        
        Args:
            to: Recipient's chat ID
            content: Message content to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self._bot:
            logger.error("Telegram bot not initialized")
            return False
            
        try:
            chat_id = to
            
            if isinstance(content, TextMessageContent):
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=content.text,
                    parse_mode=ParseMode.HTML
                )
                return True
                
            elif isinstance(content, TemplateMessageContent):
                # Handle template content (convert to Telegram format)
                text = self._format_template_message(content.template_name, content.template_data)
                reply_markup = None
                
                # Add buttons if present in template data
                if "buttons" in content.template_data:
                    reply_markup = self._create_keyboard(content.template_data["buttons"])
                
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return True
                
            elif isinstance(content, ImageMessageContent):
                caption = content.caption if content.caption else None
                
                await self._bot.send_photo(
                    chat_id=chat_id,
                    photo=content.url,
                    caption=caption,
                    parse_mode=ParseMode.HTML if caption else None
                )
                return True
                
            else:
                logger.error(f"Unsupported message content type: {type(content)}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def _format_template_message(self, template_name: str, template_data: Dict[str, Any]) -> str:
        """
        Format a template message for Telegram.
        
        Args:
            template_name: Name of the template
            template_data: Template data
            
        Returns:
            Formatted message text
        """
        # For a greeting template, create a simple welcome message
        if template_name == settings.whatsapp_greeting_template:
            return "Здравствуйте! Я бот салона красоты. Я помогу вам записаться на процедуру. Подскажите, пожалуйста, как к вам обращаться?"
        
        # If header is present, make it bold
        message_parts = []
        if "header" in template_data:
            message_parts.append(f"<b>{template_data['header']}</b>")
        
        # Add body parameters
        if "body" in template_data and isinstance(template_data["body"], list):
            for param in template_data["body"]:
                message_parts.append(param)
        
        # Return combined message
        return "\n\n".join(message_parts)
    
    def _create_keyboard(self, buttons: List[str]) -> InlineKeyboardMarkup:
        """
        Create a Telegram inline keyboard from buttons.
        
        Args:
            buttons: List of button labels
            
        Returns:
            Telegram InlineKeyboardMarkup object
        """
        keyboard = []
        for button in buttons:
            keyboard.append([InlineKeyboardButton(text=button, callback_data=button)])
            
        return InlineKeyboardMarkup(keyboard)
    
    async def parse_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook data from Telegram.
        
        Args:
            data: The webhook payload
            
        Returns:
            Parsed message information or None if not a valid message
        """
        try:
            logger.debug(f"Parsing Telegram webhook data: {data}")
            
            # Create an Update object from the webhook data
            update = Update.de_json(data, self._bot)
            
            # First check if this is a callback query (button press)
            if update.callback_query:
                callback_query = update.callback_query
                chat = callback_query.message.chat if callback_query.message else None
                
                if not chat:
                    logger.debug("No chat in Telegram callback query")
                    return None
                    
                return {
                    "platform": "telegram",
                    "sender_id": str(callback_query.from_user.id),
                    "chat_id": str(chat.id),
                    "message": callback_query.data,  # Button data as message
                    "message_type": "text",
                    "timestamp": "",  # Telegram doesn't provide timestamp in callback queries
                    "phone_number": "",  # No phone number in Telegram
                    "is_callback": True
                }
            
            # Check for regular message
            if not update.message:
                logger.debug("No message in Telegram update")
                return None
                
            message = update.message
            
            # Get sender info
            from_user = message.from_user
            if not from_user:
                logger.debug("No sender in Telegram message")
                return None
                
            # Get chat info
            chat = message.chat
            if not chat:
                logger.debug("No chat in Telegram message")
                return None
            
            result = {
                "platform": "telegram",
                "sender_id": str(from_user.id),
                "chat_id": str(chat.id),
                "phone_number": "",  # Telegram doesn't provide phone numbers
                "timestamp": str(message.date.timestamp()) if message.date else "",
                "message_type": "text",  # Default type
                "message": ""  # Default empty message
            }
            
            # Extract message content based on type
            if message.text:
                result["message"] = message.text
                result["message_type"] = "text"
            elif message.photo:
                result["message"] = message.caption or "[Image received]"
                result["message_type"] = "image"
                # Get the largest photo (last in the array)
                if message.photo:
                    result["media_id"] = message.photo[-1].file_id
            elif message.document:
                result["message"] = message.caption or "[Document received]"
                result["message_type"] = "document"
                result["media_id"] = message.document.file_id
            elif message.location:
                result["message"] = "[Location received]"
                result["message_type"] = "location"
                result["latitude"] = message.location.latitude
                result["longitude"] = message.location.longitude
            elif message.voice:
                result["message"] = "[Voice message received]"
                result["message_type"] = "voice"
                result["media_id"] = message.voice.file_id
            elif message.video:
                result["message"] = message.caption or "[Video received]"
                result["message_type"] = "video"
                result["media_id"] = message.video.file_id
            else:
                # Unknown message type
                result["message"] = "[Unsupported message type]"
            
            logger.info(f"Successfully parsed Telegram message from user {result['sender_id']}: {result['message'][:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing Telegram webhook: {e}", exc_info=True)
            return None
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set the webhook URL for the Telegram bot.
        
        Args:
            webhook_url: The webhook URL
            
        Returns:
            True if successful, False otherwise
        """
        if not self._bot:
            logger.error("Telegram bot not initialized")
            return False
            
        try:
            await self._bot.set_webhook(url=webhook_url)
            logger.info(f"Telegram webhook set to {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting Telegram webhook: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """
        Delete the webhook for the Telegram bot.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._bot:
            logger.error("Telegram bot not initialized")
            return False
            
        try:
            await self._bot.delete_webhook()
            logger.info("Telegram webhook deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting Telegram webhook: {e}")
            return False