from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from app.db.connection import db
from app.models.message import Message, MessageCreate, MessageType

class MessageRepository:
    """Repository for message data access operations."""
    
    @staticmethod
    async def create(conversation_id: UUID, message: MessageCreate) -> Message:
        """Create a new message in the database."""
        query = """
        INSERT INTO message (
            id, conversation_id, content, message_type, timestamp, sender_id, is_from_bot
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7
        ) RETURNING *
        """
        
        message_id = uuid4()
        timestamp = datetime.now()
        
        values = (
            message_id,
            conversation_id,
            message.content,
            message.message_type.value,
            timestamp,
            message.sender_id,
            message.is_from_bot
        )
        
        row = await db.fetchrow(query, *values)
        return Message.model_validate(row)
    
    @staticmethod
    async def get_by_id(message_id: UUID) -> Optional[Message]:
        """Get a message by its ID."""
        query = "SELECT * FROM message WHERE id = $1"
        row = await db.fetchrow(query, message_id)
        if row:
            return Message.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_conversation(conversation_id: UUID, limit: int = 100, offset: int = 0) -> List[Message]:
        """Get messages for a conversation with pagination."""
        query = """
        SELECT * FROM message 
        WHERE conversation_id = $1 
        ORDER BY timestamp ASC
        LIMIT $2 OFFSET $3
        """
        rows = await db.fetch(query, conversation_id, limit, offset)
        return [Message.model_validate(row) for row in rows]
    
    @staticmethod
    async def count_by_conversation(conversation_id: UUID) -> int:
        """Count the number of messages in a conversation."""
        query = "SELECT COUNT(*) FROM message WHERE conversation_id = $1"
        count = await db.fetchval(query, conversation_id)
        return count
    
    @staticmethod
    async def get_conversation_history(conversation_id: UUID, only_complete = False) -> List[Message]:
        """Get all active messages for a conversation in order."""
        only_complete_query = """
        SELECT * FROM message 
        WHERE conversation_id = $1 AND is_complete = FALSE 
        ORDER BY timestamp ASC
        """
        all_query = """
        SELECT * FROM message
        WHERE conversation_id = $1
        ORDER BY timestamp ASC
        """
        query = only_complete_query if only_complete else all_query
        rows = await db.fetch(query, conversation_id)
        return [Message.model_validate(row) for row in rows]
        
    @staticmethod
    async def delete(message_id: UUID) -> bool:
        """Delete a message."""
        query = "DELETE FROM message WHERE id = $1 RETURNING id"
        result = await db.fetchval(query, message_id)
        return result is not None
    
    @staticmethod
    async def delete_by_conversation(conversation_id: UUID) -> int:
        """Delete all messages for a conversation and return the count of deleted messages."""
        query = "DELETE FROM message WHERE conversation_id = $1 RETURNING id"
        rows = await db.fetch(query, conversation_id)
        return len(rows)
      
    @staticmethod
    async def mark_conversation_messages_as_complete(conversation_id: UUID) -> int:
        """
        Mark all messages in a conversation as 'complete' when a booking is finalized.
        This helps to separate old conversations from new ones.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Number of messages marked as complete
        """
        query = """
        UPDATE message 
        SET is_complete = TRUE 
        WHERE conversation_id = $1 AND is_complete = FALSE
        RETURNING id
        """
        rows = await db.fetch(query, conversation_id)
        return len(rows)