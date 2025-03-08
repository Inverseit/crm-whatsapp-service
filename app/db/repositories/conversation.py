from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import phonenumbers

from app.db.connection import db
from app.models.conversation import Conversation, ConversationCreate, ConversationUpdate, ConversationState

class ConversationRepository:
    """Repository for conversation data access operations."""
    
    @staticmethod
    async def create(conversation: ConversationCreate) -> Conversation:
        """Create a new conversation in the database."""
        query = """
        INSERT INTO conversation (
            id, phone_number, state, is_complete
        ) VALUES (
            $1, $2, $3, $4
        ) RETURNING *
        """
        
        # Normalize phone number
        phone_number = conversation.phone_number
        try:
            parsed_number = phonenumbers.parse(phone_number, "KZ")
            if phonenumbers.is_valid_number(parsed_number):
                phone_number = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
        except Exception:
            pass  # Use the original number if parsing fails
        
        conversation_id = uuid4()
        values = (
            conversation_id,
            phone_number,
            conversation.state.value,
            conversation.is_complete
        )
        
        row = await db.fetchrow(query, *values)
        return Conversation.model_validate(row)
    
    @staticmethod
    async def get_by_id(conversation_id: UUID) -> Optional[Conversation]:
        """Get a conversation by its ID."""
        query = "SELECT * FROM conversation WHERE id = $1"
        row = await db.fetchrow(query, conversation_id)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_phone(phone_number: str) -> Optional[Conversation]:
        """Get a conversation by phone number."""
        # Try to normalize the phone number for lookup
        try:
            parsed_number = phonenumbers.parse(phone_number, "KZ")
            if phonenumbers.is_valid_number(parsed_number):
                normalized_phone = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
                
                query = "SELECT * FROM conversation WHERE phone_number = $1"
                row = await db.fetchrow(query, normalized_phone)
                if row:
                    return Conversation.model_validate(row)
        except Exception:
            pass  # If parsing fails, try with the original number
            
        # Try with the original number
        query = "SELECT * FROM conversation WHERE phone_number = $1"
        row = await db.fetchrow(query, phone_number)
        if row:
            return Conversation.model_validate(row)
            
        return None
    
    @staticmethod
    async def get_all() -> List[Conversation]:
        """Get all conversations."""
        query = "SELECT * FROM conversation ORDER BY last_updated DESC"
        rows = await db.fetch(query)
        return [Conversation.model_validate(row) for row in rows]
    
    @staticmethod
    async def update(conversation_id: UUID, conversation_update: ConversationUpdate | dict) -> Optional[Conversation]:
        """Update a conversation."""
        # First check if conversation exists
        conversation = await ConversationRepository.get_by_id(conversation_id)
        if not conversation:
            return None
        
        # Build update query dynamically based on provided fields
        update_parts = []
        values = [conversation_id]  # First parameter is always the conversation ID
        param_idx = 2  # Start parameter index at 2
        
        # For each field in the update model, add it to the query if it's not None
        if isinstance(conversation_update, dict):
            conversation_update = ConversationUpdate(**conversation_update)
        fields = conversation_update.model_dump(exclude_none=True)
        for field_name, value in fields.items():
            # Handle enum values
            if isinstance(value, ConversationState):
                value = value.value
                
            update_parts.append(f"{field_name} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        # If there are no fields to update, return the original conversation
        if not update_parts:
            return conversation
        
        # Build the complete query
        update_clause = ", ".join(update_parts)
        query = f"UPDATE conversation SET {update_clause}, last_updated = NOW() WHERE id = $1 RETURNING *"
        
        # Execute update
        row = await db.fetchrow(query, *values)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def delete(conversation_id: UUID) -> bool:
        """Delete a conversation."""
        query = "DELETE FROM conversation WHERE id = $1 RETURNING id"
        result = await db.fetchval(query, conversation_id)
        return result is not None
    
    @staticmethod
    async def get_active_conversations() -> List[Conversation]:
        """Get all active (incomplete) conversations."""
        query = "SELECT * FROM conversation WHERE is_complete = FALSE ORDER BY last_updated DESC"
        rows = await db.fetch(query)
        return [Conversation.model_validate(row) for row in rows]
    
    @staticmethod
    async def get_or_create(phone_number: str) -> Conversation:
        """Get an existing conversation by phone or create a new one."""
        conversation = await ConversationRepository.get_by_phone(phone_number)
        if conversation:
            return conversation
        
        new_conversation = ConversationCreate(
            phone_number=phone_number
        )
        return await ConversationRepository.create(new_conversation)