# app/models/conversation.py
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ConversationState(str, Enum):
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    CONFIRMING = "confirming"
    COMPLETED = "completed"

class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    phone_number: str
    state: ConversationState = ConversationState.GREETING
    is_complete: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)

class ConversationCreate(BaseModel):
    phone_number: str
    state: ConversationState = ConversationState.GREETING
    is_complete: bool = False

class ConversationUpdate(BaseModel):
    state: Optional[ConversationState] = None
    is_complete: Optional[bool] = None