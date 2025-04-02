# app/models/message.py
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

from app.models.conversation import MessagingPlatform

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"

class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.now)
    sender_id: str
    is_from_bot: bool = False
    is_complete: bool = False # We mark true when we have confirmed a booking.
    platform: MessagingPlatform = MessagingPlatform.WHATSAPP
    
    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    sender_id: str
    is_from_bot: bool = False
    platform: MessagingPlatform = MessagingPlatform.WHATSAPP

class WebhookMessage(BaseModel):
    phone_number: str
    message: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.now)
    platform: MessagingPlatform = MessagingPlatform.GENERIC
    telegram_id: str = ""
    telegram_chat_id: str = ""
    whatsapp_id: str = ""