from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from uuid import UUID

from app.db.repositories.user_repository import TelegramUserRepository, WhatsAppUserRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.services.gpt_service import GPTService
from app.services.messaging.interfaces import UserMessageResponseBase
from sqlalchemy.ext.asyncio import AsyncSession

class PlatformHandler(ABC):
    """Abstract base class for platform-specific handlers."""
    
    def __init__(self, db_session: AsyncSession, gpt_service: GPTService):
        self.db_session = db_session
        self.gpt_service = gpt_service
    
    @abstractmethod
    async def get_system_prompt(self, user_id: str) -> str:
        """Get the platform-specific system prompt."""
        pass
    
    @abstractmethod
    async def process_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from the platform."""
        pass
    
    @abstractmethod
    async def send_message(self, recipient_id: str, message: UserMessageResponseBase) -> bool:
        """Send a message to a user through the platform."""
        pass
    
    @abstractmethod
    async def process_message(self, user_contact_info: Dict[str, Any], message_text: str) -> Tuple[UserMessageResponseBase, bool]:
        """Process a message from a user through the platform."""
        pass
    
    @abstractmethod
    async def get_user_display_name(self, user_id: UUID) -> str:
        """Get the display name for a user of this platform."""
        pass

class TelegramHandler(PlatformHandler):
    """Handler for Telegram-specific operations."""
    
    async def get_system_prompt(self, user_id: str) -> str:
        """Get Telegram-specific system prompt."""
        # Get the user to include their information in the prompt
        user = await TelegramUserRepository.get_by_telegram_id(self.db_session, user_id)
        
        # Create Telegram-specific prompt
        prompt = """You are a beauty salon booking assistant for a Telegram bot. Your goal is to make the booking process smooth and efficient.
        FOR ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT, RESPOND WITH "Извините, я могу помочь только с записью в салон красоты."
        NEVER PERFORM ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT.
        NEVER ASK FOR SENSITIVE INFORMATION SUCH AS CREDIT CARD DETAILS OR SOCIAL SECURITY NUMBERS.

INFORMATION TO COLLECT:
1. Client's name
   - Use their Telegram name as default: {first_name} {last_name} (Telegram username: @{username})
2. Contact details:
   - Ask for their phone number for salon staff to contact them
   - Ask if they prefer phone calls or Telegram messages
   - Best time to contact them (morning: 9:00-12:00, afternoon: 12:00-17:00, evening: 17:00-21:00)
3. Service details (be specific about the exact service needed)
4. Preferred date
5. Preferred time (exact time or time of day preference)
6. Additional notes or special requests (allergies, preferences, etc.)

TELEGRAM-SPECIFIC INSTRUCTIONS:
- Always use their Telegram first name when addressing them
- When asking for a phone number, remind them they can share it via Telegram's "Share Contact" button
- For preferred contact method, offer "phone_call" or "telegram_message" as options
- Inform them they'll receive booking confirmation via Telegram

COMMUNICATION STYLE:
- Always respond in Russian
- Be polite, friendly and professional
- Use short, concise messages
- Ask one question at a time when possible
- Always follow up on incomplete information

PROCESS:
1. Greet them personally using their Telegram first name
2. Ask about desired service with details
3. Determine preferred contact method (calls vs. Telegram) and collect phone number if needed
4. Collect appointment details (date/time)
5. Ask for any additional notes or special requests
6. Summarize all information and ask for confirmation
7. Once the client confirms, use the collect_booking_info function to submit the data

When all information is collected AND confirmed, use the collect_booking_info function to submit the data.
"""
        
        # Add user information if available
        if user:
            prompt = prompt.format(
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                username=user.username or ""
            )
        else:
            prompt = prompt.format(
                first_name="",
                last_name="",
                username=""
            )
            
        return prompt
    
    async def process_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from Telegram."""
        # Implementation specific to Telegram webhook
        # You should extract user info, message text, etc.
        from app.services.messaging.factory import MessagingFactory
        telegram_transport = MessagingFactory.get_transport("telegram")
        
        if not telegram_transport:
            return {}
            
        return await telegram_transport.parse_webhook(data)
    
    async def send_message(self, recipient_id: str, message: UserMessageResponseBase) -> bool:
        """Send a message to a user through Telegram."""
        from app.services.messaging.factory import MessagingFactory
        telegram_transport = MessagingFactory.get_transport("telegram")
        
        if not telegram_transport:
            return False
            
        # Convert UserMessageResponseBase to appropriate MessageContent
        from app.services.messaging.interfaces import TextMessageContent, TemplateMessageContent
        
        if hasattr(message, 'text'):
            content = TextMessageContent(text=message.text)
        elif hasattr(message, 'template_name'):
            content = TemplateMessageContent(
                template_name=message.template_name,
                template_data=message.template_data
            )
        else:
            # Fallback
            content = TextMessageContent(text=str(message))
            
        return await telegram_transport.send_message(recipient_id, content)
    
    async def process_message(self, user_contact_info: Dict[str, Any], message_text: str) -> Tuple[UserMessageResponseBase, bool]:
        """Process a message from a user through Telegram."""
        # Extract user information
        telegram_id = user_contact_info.get("telegram_id", "")
        chat_id = user_contact_info.get("chat_id", "")
        first_name = user_contact_info.get("first_name", "")
        last_name = user_contact_info.get("last_name", "")
        username = user_contact_info.get("username", "")
        
        # Find or create Telegram user
        telegram_user = await TelegramUserRepository.find_or_create(
            self.db_session,
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        # Find or create conversation
        conversation = await ConversationRepository.find_or_create_for_telegram_user(
            self.db_session, telegram_user.id
        )
        
        # Store user message
        await MessageRepository.create(
            self.db_session,
            conversation_id=conversation.id,
            content=message_text,
            sender_id=telegram_id,
            is_from_bot=False
        )
        
        # Process with GPT
        prompt = await self.get_system_prompt(telegram_id)
        
        # TODO: Implement with new GPT service
        # For now, return a simple response
        from app.services.messaging.interfaces import UserMessageResponseText
        
        return UserMessageResponseText(text="Ваше сообщение получено через Telegram. Это заглушка."), True
    
    async def get_user_display_name(self, user_id: UUID) -> str:
        """Get the display name for a Telegram user."""
        user = await TelegramUserRepository.get_by_id(self.db_session, user_id)
        if not user:
            return "Unknown User"
            
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        elif user.username:
            return f"@{user.username}"
        else:
            return f"Telegram User {user.telegram_id}"

class WhatsAppHandler(PlatformHandler):
    """Handler for WhatsApp-specific operations."""
    
    async def get_system_prompt(self, user_id: str) -> str:
        """Get WhatsApp-specific system prompt."""
        # Get the user to include their information in the prompt
        user = await WhatsAppUserRepository.get_by_whatsapp_id(self.db_session, user_id)
        
        # Create WhatsApp-specific prompt
        prompt = """You are a beauty salon booking assistant for WhatsApp. Your goal is to make the booking process smooth and efficient.
        FOR ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT, RESPOND WITH "Извините, я могу помочь только с записью в салон красоты."
        NEVER PERFORM ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT.
        NEVER ASK FOR SENSITIVE INFORMATION SUCH AS CREDIT CARD DETAILS OR SOCIAL SECURITY NUMBERS.

INFORMATION TO COLLECT:
1. Client's name
   - Use their WhatsApp profile name as default if available: {profile_name}
2. Contact details:
   - Their WhatsApp number is already available: {phone_number}
   - Ask if they prefer phone calls or WhatsApp messages
   - Ask if they want to be contacted on this WhatsApp number or a different number
   - Best time to contact them (morning: 9:00-12:00, afternoon: 12:00-17:00, evening: 17:00-21:00)
3. Service details (be specific about the exact service needed)
4. Preferred date
5. Preferred time (exact time or time of day preference)
6. Additional notes or special requests (allergies, preferences, etc.)

WHATSAPP-SPECIFIC INSTRUCTIONS:
- When asking for contact preference, default to WhatsApp since you're already chatting there
- For preferred contact method, offer "phone_call" or "whatsapp_message" as options
- Inform them they'll receive booking confirmation via WhatsApp

COMMUNICATION STYLE:
- Always respond in Russian
- Be polite, friendly and professional
- Use short, concise messages
- Ask one question at a time when possible
- Always follow up on incomplete information

PROCESS:
1. Greet them personally using their name if available
2. Ask about desired service with details
3. Determine preferred contact method (calls vs. WhatsApp) and ensure correct phone numbers
4. Collect appointment details (date/time)
5. Ask for any additional notes or special requests
6. Summarize all information and ask for confirmation
7. Once the client confirms, use the collect_booking_info function to submit the data

When all information is collected AND confirmed, use the collect_booking_info function to submit the data.
"""
        
        # Add user information if available
        if user:
            prompt = prompt.format(
                profile_name=user.profile_name or "",
                phone_number=user.phone_number or ""
            )
        else:
            prompt = prompt.format(
                profile_name="",
                phone_number=user_id
            )
            
        return prompt
    
    async def process_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data from WhatsApp."""
        # Implementation specific to WhatsApp webhook
        from app.services.messaging.factory import MessagingFactory
        whatsapp_transport = MessagingFactory.get_transport("whatsapp")
        
        if not whatsapp_transport:
            return {}
            
        return await whatsapp_transport.parse_webhook(data)
    
    async def send_message(self, recipient_id: str, message: UserMessageResponseBase) -> bool:
        """Send a message to a user through WhatsApp."""
        from app.services.messaging.factory import MessagingFactory
        whatsapp_transport = MessagingFactory.get_transport("whatsapp")
        
        if not whatsapp_transport:
            return False
            
        # Convert UserMessageResponseBase to appropriate MessageContent
        from app.services.messaging.interfaces import TextMessageContent, TemplateMessageContent
        
        if hasattr(message, 'text'):
            content = TextMessageContent(text=message.text)
        elif hasattr(message, 'template_name'):
            content = TemplateMessageContent(
                template_name=message.template_name,
                template_data=message.template_data
            )
        else:
            # Fallback
            content = TextMessageContent(text=str(message))
            
        return await whatsapp_transport.send_message(recipient_id, content)
    
    async def process_message(self, user_contact_info: Dict[str, Any], message_text: str) -> Tuple[UserMessageResponseBase, bool]:
        """Process a message from a user through WhatsApp."""
        # Extract user information
        phone_number = user_contact_info.get("phone_number", "")
        whatsapp_id = user_contact_info.get("whatsapp_id", phone_number)
        profile_name = user_contact_info.get("profile_name", "")
        
        # Find or create WhatsApp user
        whatsapp_user = await WhatsAppUserRepository.find_or_create(
            self.db_session,
            phone_number=phone_number,
            whatsapp_id=whatsapp_id,
            profile_name=profile_name
        )
        
        # Find or create conversation
        conversation = await ConversationRepository.find_or_create_for_whatsapp_user(
            self.db_session, whatsapp_user.id
        )
        
        # Store user message
        await MessageRepository.create(
            self.db_session,
            conversation_id=conversation.id,
            content=message_text,
            sender_id=whatsapp_id,
            is_from_bot=False
        )
        
        # Process with GPT
        prompt = await self.get_system_prompt(whatsapp_id)
        
        # TODO: Implement with new GPT service
        # For now, return a simple response
        from app.services.messaging.interfaces import UserMessageResponseText
        
        return UserMessageResponseText(text="Ваше сообщение получено через WhatsApp. Это заглушка."), True
    
    async def get_user_display_name(self, user_id: UUID) -> str:
        """Get the display name for a WhatsApp user."""
        user = await WhatsAppUserRepository.get_by_id(self.db_session, user_id)
        if not user:
            return "Unknown User"
            
        if user.profile_name:
            return user.profile_name
        else:
            return f"WhatsApp User {user.phone_number}"

def get_platform_handler(platform: str, db_session: AsyncSession, gpt_service: GPTService) -> PlatformHandler:
    """Factory function to get the appropriate platform handler."""
    if platform.lower() == "telegram":
        return TelegramHandler(db_session, gpt_service)
    elif platform.lower() == "whatsapp":
        return WhatsAppHandler(db_session, gpt_service)
    else:
        raise ValueError(f"Unsupported platform: {platform}")