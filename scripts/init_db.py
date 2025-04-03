#!/usr/bin/env python3
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import settings
from app.db.base import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_database():
    """Create database tables using SQLAlchemy models."""
    try:
        # Create engine with correct URL
        engine = create_async_engine(
            settings.database_url_async,
            echo=settings.debug
        )
        
        logger.info("Creating database tables...")
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully!")
        
        # Close engine
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_database())