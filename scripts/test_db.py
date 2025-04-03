#!/usr/bin/env python3
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base
from app.db.repositories.user_repository import TelegramUserRepository, WhatsAppUserRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.models import TimeOfDay, ContactMethod, BookingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database():
    """Test database functionality by creating and retrieving entities."""
    try:
        # Create engine with correct URL
        engine = create_async_engine(
            settings.database_url_async,
            echo=settings.debug
        )
        
        # Create session factory
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create a session
        async with async_session() as session:
            # Create test Telegram user
            telegram_user = await TelegramUserRepository.create(
                session,
                telegram_id="12345",
                chat_id="12345",
                username="test_user",
                first_name="Test",
                last_name="User"
            )
            logger.info(f"Created Telegram user with ID: {telegram_user.id}")
            
            # Create test WhatsApp user
            whatsapp_user = await WhatsAppUserRepository.create(
                session,
                phone_number="+77771234567",
                whatsapp_id="77771234567",
                profile_name="Test WhatsApp User"
            )
            logger.info(f"Created WhatsApp user with ID: {whatsapp_user.id}")
            
            # Create conversations for each user
            telegram_conversation = await ConversationRepository.create(
                session,
                platform="telegram",
                user_id=telegram_user.id
            )
            logger.info(f"Created Telegram conversation with ID: {telegram_conversation.id}")
            
            whatsapp_conversation = await ConversationRepository.create(
                session,
                platform="whatsapp",
                user_id=whatsapp_user.id
            )
            logger.info(f"Created WhatsApp conversation with ID: {whatsapp_conversation.id}")
            
            # Commit the changes
            await session.commit()
        
        # Close engine
        await engine.dispose()
        
        logger.info("Database test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_database())