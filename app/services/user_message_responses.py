from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

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