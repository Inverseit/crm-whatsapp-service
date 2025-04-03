from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.db.models import MessageType

class MessageBase(BaseModel):
    """Base model for message data."""
    content: str
    message_type: MessageType = MessageType.TEXT
    sender_id: str
    is_from_bot: bool = False

class MessageCreate(MessageBase):
    """Model for creating a new message."""
    pass

class MessageResponse(MessageBase):
    """Complete message model for API responses."""
    id: UUID
    conversation_id: UUID
    timestamp: datetime
    is_complete: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class WebhookMessage(BaseModel):
    """Model for receiving messages from external webhooks."""
    # Platform-agnostic fields
    message: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    
    # Platform-specific fields - only relevant ones will be populated
    platform: str = Field(..., description="Messaging platform (telegram, whatsapp)")
    
    # WhatsApp fields
    phone_number: str = Field("", description="Sender's phone number (WhatsApp)")
    whatsapp_id: str = Field("", description="WhatsApp ID")
    
    # Telegram fields
    telegram_id: str = Field("", description="Telegram user ID")
    telegram_chat_id: str = Field("", description="Telegram chat ID")
    telegram_username: str = Field("", description="Telegram username")
    first_name: str = Field("", description="Sender's first name (Telegram)")
    last_name: str = Field("", description="Sender's last name (Telegram)")
    
    # Media fields (optional)
    media_id: str = Field("", description="Media ID for non-text messages")
    media_url: str = Field("", description="Media URL for non-text messages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "whatsapp",
                "phone_number": "+77771234567",
                "message": "Hello, I want to book a haircut",
                "message_type": "text",
                "timestamp": "2025-04-03T12:00:00Z"
            }
        }
    )