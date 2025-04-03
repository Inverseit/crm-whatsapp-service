from uuid import UUID
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.models import Message, MessageType, Conversation

class MessageRepository:
    """Repository for message data access operations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        conversation_id: UUID,
        content: str,
        sender_id: str,
        is_from_bot: bool = False,
        message_type: MessageType = MessageType.TEXT,
        is_complete: bool = False
    ) -> Message:
        """Create a new message in the database."""
        message = Message(
            conversation_id=conversation_id,
            content=content,
            message_type=message_type,
            sender_id=sender_id,
            is_from_bot=is_from_bot,
            is_complete=is_complete
        )
        
        session.add(message)
        await session.flush()
        return message
    
    @staticmethod
    async def get_by_id(session: AsyncSession, message_id: UUID) -> Optional[Message]:
        """Get a message by its ID."""
        result = await session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_conversation(
        session: AsyncSession, 
        conversation_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation with pagination."""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def count_by_conversation(session: AsyncSession, conversation_id: UUID) -> int:
        """Count the number of messages in a conversation."""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return len(list(result.scalars().all()))
    
    @staticmethod
    async def get_conversation_history(
        session: AsyncSession,
        conversation_id: UUID,
        only_complete: bool = False
    ) -> List[Message]:
        """Get all messages for a conversation in chronological order."""
        if only_complete:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .where(Message.is_complete == False)
                .order_by(Message.timestamp.asc())
            )
        else:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.asc())
            )
            
        return list(result.scalars().all())
    
    @staticmethod
    async def delete(session: AsyncSession, message_id: UUID) -> bool:
        """Delete a message."""
        message = await MessageRepository.get_by_id(session, message_id)
        if not message:
            return False
            
        await session.delete(message)
        await session.flush()
        return True
    
    @staticmethod
    async def delete_by_conversation(session: AsyncSession, conversation_id: UUID) -> int:
        """Delete all messages for a conversation and return the count of deleted messages."""
        messages = await MessageRepository.get_by_conversation(
            session, conversation_id, limit=10000
        )
        count = 0
        
        for message in messages:
            await session.delete(message)
            count += 1
            
        await session.flush()
        return count
    
    @staticmethod
    async def mark_conversation_messages_as_complete(session: AsyncSession, conversation_id: UUID) -> int:
        """Mark all messages in a conversation as 'complete' when a booking is finalized."""
        messages = await MessageRepository.get_by_conversation(
            session, conversation_id, limit=10000
        )
        count = 0
        
        for message in messages:
            if not message.is_complete:
                message.is_complete = True
                session.add(message)
                count += 1
                
        await session.flush()
        return count