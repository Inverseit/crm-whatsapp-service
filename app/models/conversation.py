# app/models/conversation.py
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ConversationState(str, Enum):
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    COMPLETED = "completed"


class MessagingPlatform(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    GENERIC = "generic"


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    
    # Contact information
    phone_number: str = Field("", description="Phone number in E.164 format (primary identifier for WhatsApp)")
    whatsapp_id: str = Field("", description="WhatsApp identifier (usually same as phone number)")
    telegram_id: str = Field("", description="Telegram user ID")
    telegram_chat_id: str = Field("", description="Telegram chat ID (can differ from user ID in group chats)")
    
    # Contact's preferred platform
    primary_platform: MessagingPlatform = Field(default=MessagingPlatform.WHATSAPP, description="User's primary messaging platform")
    
    # Conversation state
    state: ConversationState = Field(default=ConversationState.GREETING)
    is_complete: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)
    
    def get_platform_id(self, platform: MessagingPlatform) -> str:
        """
        Get the appropriate identifier for a given platform.
        
        Args:
            platform: The messaging platform
            
        Returns:
            The platform-specific identifier
        """
        if platform == MessagingPlatform.WHATSAPP:
            return self.whatsapp_id or self.phone_number
        elif platform == MessagingPlatform.TELEGRAM:
            return self.telegram_chat_id or self.telegram_id
        return self.phone_number  # Fallback to phone number for generic platform


class ConversationCreate(BaseModel):
    phone_number: str = Field("", description="Phone number in E.164 format")
    whatsapp_id: str = Field("", description="WhatsApp identifier")
    telegram_id: str = Field("", description="Telegram user ID")
    telegram_chat_id: str = Field("", description="Telegram chat ID")
    primary_platform: MessagingPlatform = Field(default=MessagingPlatform.WHATSAPP)
    state: ConversationState = Field(default=ConversationState.GREETING)
    is_complete: bool = Field(default=False)


class ConversationUpdate(BaseModel):
    phone_number: Optional[str] = None
    whatsapp_id: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    primary_platform: Optional[MessagingPlatform] = None
    state: Optional[ConversationState] = None
    is_complete: Optional[bool] = None