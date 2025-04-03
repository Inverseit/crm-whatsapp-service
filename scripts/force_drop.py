#!/usr/bin/env python3
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def force_drop_types():
    """
    Force drops the enum types from all schemas, regardless of visibility issues.
    """
    try:
        # Create engine with correct URL
        engine = create_async_engine(
            settings.database_url_async,
            echo=True
        )
        
        logger.info("Forcibly dropping enum types...")
        
        async with engine.begin() as conn:
            # Drop each type with IF EXISTS and CASCADE to force removal
            for enum_name in ['conversation_state', 'booking_status', 'time_of_day', 'contact_method', 'message_type']:
                try:
                    # This should work regardless of schema issues
                    await conn.execute(text(f"""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
                        ) THEN
                            EXECUTE 'DROP TYPE "{enum_name}" CASCADE';
                        END IF;
                    END
                    $$;
                    """))
                    logger.info(f"Attempted to drop {enum_name}")
                except Exception as e:
                    logger.warning(f"Error dropping {enum_name}: {e}")
        
        # Close engine
        await engine.dispose()
        
        logger.info("Type cleanup complete!")
        return True
        
    except Exception as e:
        logger.error(f"Error in force_drop_types: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(force_drop_types())