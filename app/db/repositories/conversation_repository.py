from uuid import UUID
from typing import Optional, List, Literal
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, ConversationState, TelegramUser, WhatsAppUser

class ConversationRepository:
    """Repository for conversation data access operations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        platform: Literal["telegram", "whatsapp"],
        user_id: UUID,
        state: ConversationState = ConversationState.GREETING,
        is_complete: bool = False
    ) -> Conversation:
        """Create a new conversation in the database."""
        conversation = Conversation(
            state=state,
            is_complete=is_complete,
            platform=platform
        )
        
        # Set the appropriate user ID based on platform
        if platform == "telegram":
            conversation.telegram_user_id = user_id
        elif platform == "whatsapp":
            conversation.whatsapp_user_id = user_id
        
        session.add(conversation)
        await session.flush()
        return conversation
    
    @staticmethod
    async def get_by_id(session: AsyncSession, conversation_id: UUID) -> Optional[Conversation]:
        """Get a conversation by its ID."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_telegram_user(session: AsyncSession, telegram_user_id: UUID) -> List[Conversation]:
        """Get conversations for a Telegram user."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.telegram_user_id == telegram_user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_whatsapp_user(session: AsyncSession, whatsapp_user_id: UUID) -> List[Conversation]:
        """Get conversations for a WhatsApp user."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.whatsapp_user_id == whatsapp_user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_active_by_telegram_user(session: AsyncSession, telegram_user_id: UUID) -> Optional[Conversation]:
        """Get the active conversation for a Telegram user."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.telegram_user_id == telegram_user_id)
            .where(Conversation.is_complete == False)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_active_by_whatsapp_user(session: AsyncSession, whatsapp_user_id: UUID) -> Optional[Conversation]:
        """Get the active conversation for a WhatsApp user."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.whatsapp_user_id == whatsapp_user_id)
            .where(Conversation.is_complete == False)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().first()
    
    @staticmethod
    async def update(
        session: AsyncSession, 
        conversation_id: UUID, 
        **kwargs
    ) -> Optional[Conversation]:
        """Update a conversation."""
        conversation = await ConversationRepository.get_by_id(session, conversation_id)
        if not conversation:
            return None
            
        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
                
        session.add(conversation)
        await session.flush()
        return conversation
    
    @staticmethod
    async def find_or_create_for_telegram_user(
        session: AsyncSession,
        telegram_user_id: UUID,
        create_if_missing: bool = True
    ) -> Optional[Conversation]:
        """Find an active conversation for a Telegram user or create a new one."""
        # Try to find an active conversation
        conversation = await ConversationRepository.get_active_by_telegram_user(session, telegram_user_id)
        
        if not conversation and create_if_missing:
            # Create a new conversation if none exists
            conversation = await ConversationRepository.create(
                session,
                platform="telegram",
                user_id=telegram_user_id
            )
            
        return conversation
    
    @staticmethod
    async def find_or_create_for_whatsapp_user(
        session: AsyncSession,
        whatsapp_user_id: UUID,
        create_if_missing: bool = True
    ) -> Optional[Conversation]:
        """Find an active conversation for a WhatsApp user or create a new one."""
        # Try to find an active conversation
        conversation = await ConversationRepository.get_active_by_whatsapp_user(session, whatsapp_user_id)
        
        if not conversation and create_if_missing:
            # Create a new conversation if none exists
            conversation = await ConversationRepository.create(
                session,
                platform="whatsapp",
                user_id=whatsapp_user_id
            )
            
        return conversation
    
    @staticmethod
    async def get_all_active(session: AsyncSession) -> List[Conversation]:
        """Get all active conversations."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.is_complete == False)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_all(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """Get all conversations with pagination."""
        result = await session.execute(
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())