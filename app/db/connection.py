import asyncpg
import logging
import os
from typing import Optional, Any, Dict, List, Tuple
from asyncpg.pool import Pool

from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    """
    Database connection manager for PostgreSQL using asyncpg.
    """
    def __init__(self):
        self.pool: Optional[Pool] = None
        
    async def connect(self) -> None:
        """
        Create a connection pool to the PostgreSQL database.
        """
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=settings.database_url,
                    min_size=5,
                    max_size=20
                )
                logger.info("Connected to PostgreSQL database")
                
                # Initialize database schema
                if settings.debug:
                    await self.init_db()
                    
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
    
    async def disconnect(self) -> None:
        """
        Close all connections in the pool.
        """
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL database")
            
    async def init_db(self) -> None:
        """
        Initialize the database schema.
        """
        try:
            # Read schema.sql file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(current_dir, "schema.sql")
            
            with open(schema_path, "r") as f:
                schema = f.read()
                
            # Execute schema
            async with self.pool.acquire() as conn:
                await conn.execute(schema)
                logger.info("Database schema initialized")
                
        except Exception as e:
            logger.error(f"Error initializing database schema: {e}")
            raise
            
    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Execute a query and return the status.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)
            
    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Execute a query and return all rows as dictionaries.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            # Use the built-in Record.items() method to convert to dict
            records = await conn.fetch(query, *args, **kwargs)
            return [dict(record) for record in records]
            
    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute a query and return a single row as a dictionary.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *args, **kwargs)
            if record:
                return dict(record)
            return None
            
    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a query and return a single value.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)
    
    async def transaction(self) -> asyncpg.transaction.Transaction:
        """
        Start a transaction.
        """
        if not self.pool:
            await self.connect()
            
        # Return the connection and transaction together
        conn = await self.pool.acquire()
        tx = conn.transaction()
        await tx.start()
        
        # Return the transaction with the connection attached
        # This is a bit of a hack, but it works for simple cases
        tx._conn = conn  # type: ignore
        return tx
    
    async def commit_transaction(self, tx: asyncpg.transaction.Transaction) -> None:
        """
        Commit a transaction and release the connection.
        """
        try:
            await tx.commit()
        finally:
            # Release the connection back to the pool
            await self.pool.release(tx._conn)  # type: ignore
            
    async def rollback_transaction(self, tx: asyncpg.transaction.Transaction) -> None:
        """
        Rollback a transaction and release the connection.
        """
        try:
            await tx.rollback()
        finally:
            # Release the connection back to the pool
            await self.pool.release(tx._conn)  # type: ignore

# Create a database instance for use throughout the app
db = Database()