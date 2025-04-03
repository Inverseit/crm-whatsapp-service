from uuid import UUID
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TelegramUser, WhatsAppUser

class TelegramUserRepository:
    """Repository for Telegram user data access operations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        telegram_id: str,
        chat_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> TelegramUser:
        """Create a new Telegram user in the database."""
        user = TelegramUser(
            telegram_id=telegram_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        session.add(user)
        await session.flush()
        return user
    
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: UUID) -> Optional[TelegramUser]:
        """Get a Telegram user by their UUID."""
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.id == user_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: str) -> Optional[TelegramUser]:
        """Get a Telegram user by their Telegram ID."""
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_chat_id(session: AsyncSession, chat_id: str) -> Optional[TelegramUser]:
        """Get a Telegram user by their chat ID."""
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.chat_id == chat_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> Optional[TelegramUser]:
        """Get a Telegram user by their username."""
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.username == username)
        )
        return result.scalars().first()
    
    @staticmethod
    async def update(
        session: AsyncSession, 
        user_id: UUID, 
        **kwargs
    ) -> Optional[TelegramUser]:
        """Update a Telegram user's information."""
        user = await TelegramUserRepository.get_by_id(session, user_id)
        if not user:
            return None
            
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        session.add(user)
        await session.flush()
        return user
    
    @staticmethod
    async def find_or_create(
        session: AsyncSession,
        telegram_id: str,
        chat_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> TelegramUser:
        """Find an existing Telegram user or create a new one if not found."""
        # First try to find by telegram_id
        user = await TelegramUserRepository.get_by_telegram_id(session, telegram_id)
        if user:
            # Update user information if needed
            update_data = {}
            if chat_id != user.chat_id:
                update_data["chat_id"] = chat_id
            if username and username != user.username:
                update_data["username"] = username
            if first_name and first_name != user.first_name:
                update_data["first_name"] = first_name
            if last_name and last_name != user.last_name:
                update_data["last_name"] = last_name
            if phone_number and phone_number != user.phone_number:
                update_data["phone_number"] = phone_number
                
            if update_data:
                user = await TelegramUserRepository.update(session, user.id, **update_data)
            return user
        
        # User not found, create a new one
        return await TelegramUserRepository.create(
            session, telegram_id, chat_id, username, first_name, last_name, phone_number
        )

class WhatsAppUserRepository:
    """Repository for WhatsApp user data access operations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        phone_number: str,
        whatsapp_id: str,
        profile_name: Optional[str] = None
    ) -> WhatsAppUser:
        """Create a new WhatsApp user in the database."""
        user = WhatsAppUser(
            phone_number=phone_number,
            whatsapp_id=whatsapp_id,
            profile_name=profile_name
        )
        session.add(user)
        await session.flush()
        return user
    
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: UUID) -> Optional[WhatsAppUser]:
        """Get a WhatsApp user by their UUID."""
        result = await session.execute(
            select(WhatsAppUser).where(WhatsAppUser.id == user_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_phone(session: AsyncSession, phone_number: str) -> Optional[WhatsAppUser]:
        """Get a WhatsApp user by their phone number."""
        result = await session.execute(
            select(WhatsAppUser).where(WhatsAppUser.phone_number == phone_number)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_whatsapp_id(session: AsyncSession, whatsapp_id: str) -> Optional[WhatsAppUser]:
        """Get a WhatsApp user by their WhatsApp ID."""
        result = await session.execute(
            select(WhatsAppUser).where(WhatsAppUser.whatsapp_id == whatsapp_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def update(
        session: AsyncSession, 
        user_id: UUID, 
        **kwargs
    ) -> Optional[WhatsAppUser]:
        """Update a WhatsApp user's information."""
        user = await WhatsAppUserRepository.get_by_id(session, user_id)
        if not user:
            return None
            
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        session.add(user)
        await session.flush()
        return user
    
    @staticmethod
    async def find_or_create(
        session: AsyncSession,
        phone_number: str,
        whatsapp_id: str,
        profile_name: Optional[str] = None
    ) -> WhatsAppUser:
        """Find an existing WhatsApp user or create a new one if not found."""
        # First try to find by phone_number
        user = await WhatsAppUserRepository.get_by_phone(session, phone_number)
        if user:
            # Update user information if needed
            update_data = {}
            if whatsapp_id != user.whatsapp_id:
                update_data["whatsapp_id"] = whatsapp_id
            if profile_name and profile_name != user.profile_name:
                update_data["profile_name"] = profile_name
                
            if update_data:
                user = await WhatsAppUserRepository.update(session, user.id, **update_data)
            return user
        
        # Try to find by whatsapp_id as a fallback
        user = await WhatsAppUserRepository.get_by_whatsapp_id(session, whatsapp_id)
        if user:
            # Update user information if needed
            update_data = {}
            if phone_number != user.phone_number:
                update_data["phone_number"] = phone_number
            if profile_name and profile_name != user.profile_name:
                update_data["profile_name"] = profile_name
                
            if update_data:
                user = await WhatsAppUserRepository.update(session, user.id, **update_data)
            return user
        
        # User not found, create a new one
        return await WhatsAppUserRepository.create(
            session, phone_number, whatsapp_id, profile_name
        )