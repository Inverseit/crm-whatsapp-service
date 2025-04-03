from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, func, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.orm import relationship

from app.db.base import Base

# Define Enums
class ConversationState(str, PyEnum):
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    COMPLETED = "completed"

class BookingStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class TimeOfDay(str, PyEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"

class ContactMethod(str, PyEnum):
    PHONE_CALL = "phone_call"
    WHATSAPP_MESSAGE = "whatsapp_message"
    TELEGRAM_MESSAGE = "telegram_message"

class MessageType(str, PyEnum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"

# Base User class
class User(Base):
    """Abstract base user class that contains common fields."""
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

# Platform-specific user tables
class TelegramUser(User):
    """Telegram-specific user model."""
    __tablename__ = "telegram_user"
    
    telegram_id = Column(String(20), nullable=False, unique=True, index=True)
    chat_id = Column(String(20), nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="telegram_user", 
                               foreign_keys="Conversation.telegram_user_id")

class WhatsAppUser(User):
    """WhatsApp-specific user model."""
    __tablename__ = "whatsapp_user"
    
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    whatsapp_id = Column(String(20), nullable=False, index=True)
    profile_name = Column(String(255), nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="whatsapp_user", 
                               foreign_keys="Conversation.whatsapp_user_id")

# Main conversation model
class Conversation(Base):
    __tablename__ = "conversation"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(Enum(ConversationState), default=ConversationState.GREETING, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Foreign keys to platform-specific users (only one will be populated)
    telegram_user_id = Column(UUID(as_uuid=True), ForeignKey("telegram_user.id"), nullable=True)
    whatsapp_user_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_user.id"), nullable=True)
    
    # Platform indicator (derived from which user_id is populated)
    platform = Column(String(20), nullable=False, index=True)
    
    # Relationships
    telegram_user = relationship("TelegramUser", back_populates="conversations", 
                               foreign_keys=[telegram_user_id])
    whatsapp_user = relationship("WhatsAppUser", back_populates="conversations", 
                                foreign_keys=[whatsapp_user_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="conversation", cascade="all, delete-orphan")

# Message model
class Message(Base):
    __tablename__ = "message"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    sender_id = Column(String(255), nullable=False)
    is_from_bot = Column(Boolean, default=False, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_conversation_time', 'conversation_id', 'timestamp'),
    )

# Booking model
class Booking(Base):
    __tablename__ = "booking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False)
    
    # Client info
    client_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    use_phone_for_whatsapp = Column(Boolean, default=True, nullable=False)
    whatsapp = Column(String(20), nullable=True)
    
    # Contact preferences
    preferred_contact_method = Column(Enum(ContactMethod), nullable=False)
    preferred_contact_time = Column(Enum(TimeOfDay), nullable=True)
    
    # Service details
    service_description = Column(Text, nullable=False)
    booking_date = Column(DateTime, nullable=True)
    booking_time = Column(DateTime, nullable=True)
    time_of_day = Column(Enum(TimeOfDay), nullable=True)
    additional_notes = Column(Text, nullable=True)
    
    # Status
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="bookings")
    
    # Indexes
    __table_args__ = (
        Index('idx_booking_conversation', 'conversation_id'),
    )