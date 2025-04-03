#!/usr/bin/env python3
import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_migration_state():
    """
    Resets the migration state by dropping existing types and alembic_version table.
    Use with caution - this is meant to reset a broken migration state.
    """
    try:
        # Create engine with correct URL
        engine = create_async_engine(
            settings.database_url_async,
            echo=settings.debug
        )
        
        logger.info("Resetting migration state...")
        
        # Create all tables
        async with engine.begin() as conn:
            # Drop alembic_version table if it exists
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            logger.info("Dropped alembic_version table")
            
            # Drop existing enum types if they exist
            for enum_name in ['conversation_state', 'booking_status', 'time_of_day', 'contact_method', 'message_type']:
                try:
                    await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                    logger.info(f"Dropped enum type: {enum_name}")
                except Exception as e:
                    logger.warning(f"Could not drop enum type {enum_name}: {e}")
            
            # Commit the transaction
            # await conn.commit()
            
        logger.info("Migration state reset successfully!")
        
        # Close engine
        await engine.dispose()
        
        return True
        
    except Exception as e:
        logger.error(f"Error resetting migration state: {e}")
        return False

async def drop_tables():
    """Drop all tables in the database."""
    try:
        # Create engine with correct URL
        engine = create_async_engine(
            settings.database_url_async,
            echo=settings.debug
        )
        
        logger.info("Dropping all tables...")
        
        async with engine.begin() as conn:
            # Drop all tables in the correct order
            await conn.execute(text("DROP TABLE IF EXISTS booking CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS message CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS conversation CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS telegram_user CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS whatsapp_user CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            
            # Drop all enum types
            for enum_name in ['conversation_state', 'booking_status', 'time_of_day', 'contact_method', 'message_type']:
                try:
                    await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                except Exception as e:
                    logger.warning(f"Could not drop enum type {enum_name}: {e}")
        
        logger.info("All tables dropped successfully!")
        
        # Close engine
        await engine.dispose()
        
        return True
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop-all":
        logger.warning("WARNING: This will drop ALL tables and data in your database!")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            success = asyncio.run(drop_tables())
            if success:
                logger.info("Database reset complete. You can now run migrations.")
            else:
                logger.error("Failed to reset database.")
        else:
            logger.info("Operation cancelled.")
    else:
        logger.warning("WARNING: This will reset the Alembic migration state!")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            success = asyncio.run(reset_migration_state())
            if success:
                logger.info("Migration state reset complete. You can now run 'alembic upgrade head'.")
            else:
                logger.error("Failed to reset migration state.")
        else:
            logger.info("Operation cancelled.")