from typing import Any
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from app.config import settings

# Create async SQLAlchemy engine
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.debug,
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

# Context manager for database sessions
@asynccontextmanager
async def get_db() -> AsyncSession:
    """
    Provide a database session and handle cleanup after use.
    
    Yields:
        AsyncSession: A SQLAlchemy async session
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

class CustomBase:
    """Base class for all SQLAlchemy models."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name automatically based on class name."""
        return cls.__name__.lower()
    
    def dict(self) -> dict[str, Any]:
        """Convert model instance to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# Create the declarative base model
Base = declarative_base(cls=CustomBase)