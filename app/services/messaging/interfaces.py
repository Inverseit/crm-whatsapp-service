from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Enum for message types."""
    TEXT = "text"
    IMAGE = "image"
    TEMPLATE = "template"

@dataclass
class UserMessageResponseBase:
    message_type: MessageType

@dataclass
class UserMessageResponseText(UserMessageResponseBase):
    text: str
    message_type: MessageType = field(default=MessageType.TEXT, init=False)

@dataclass
class UserMessageResponseImage(UserMessageResponseBase):
    image_url: str
    message_type: MessageType = field(default=MessageType.IMAGE, init=False)
    
@dataclass
class UserMessageResponseTemplate(UserMessageResponseBase):
    template_name: str
    template_data: Dict[str, Any]
    message_type: MessageType = field(default=MessageType.TEMPLATE, init=False)

@dataclass
class MessageContent:
    """Base class for message content"""
    pass

@dataclass
class TextMessageContent(MessageContent):
    """Text message content"""
    text: str

@dataclass
class TemplateMessageContent(MessageContent):
    """Template message content"""
    template_name: str
    template_data: Dict[str, Any]

@dataclass
class ImageMessageContent(MessageContent):
    """Image message content"""
    url: str
    caption: Optional[str] = None

class MessagingTransport(ABC):
    """Interface for messaging transport providers"""
    
    @abstractmethod
    async def send_message(self, to: str, content: MessageContent) -> bool:
        """
        Send a message to a recipient
        
        Args:
            to: Recipient identifier (phone number, chat id, etc.)
            content: Message content to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def parse_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse webhook data from the messaging platform
        
        Args:
            data: The webhook payload
            
        Returns:
            Parsed message data or None if invalid
        """
        pass