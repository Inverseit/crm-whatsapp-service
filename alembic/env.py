import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add model's MetaData object here for 'autogenerate' support
from app.db.base import Base
from app.db.models import *  # Import all models
target_metadata = Base.metadata

# Add database URL from environment variables
from app.config import settings
config.set_main_option("sqlalchemy.url", settings.database_url_async)

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # ALWAYS try to clean up any existing enum types before running migrations
    # This ensures we don't get "type already exists" errors
    print("Cleaning up any existing enum types...")
    
    # First drop tables that might depend on these enum types
    for table_name in ['booking', 'message', 'conversation', 'telegram_user', 'whatsapp_user']:
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            print(f"Dropped table {table_name} if it existed")
        except Exception as e:
            print(f"Error dropping table {table_name}: {e}")
    
    # Then drop the enum types
    for enum_name in ['conversation_state', 'booking_status', 'time_of_day', 'contact_method', 'message_type']:
        try:
            connection.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
            print(f"Dropped enum type {enum_name} if it existed")
        except Exception as e:
            print(f"Error dropping enum type {enum_name}: {e}")
    
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    
    # Get alembic section from alembic.ini
    configuration = config.get_section(config.config_ini_section)
    
    # Replace env variables in configuration if needed
    for key, value in configuration.items():
        if isinstance(value, str) and '%(' in value and ')s' in value:
            # This looks like a template string
            for env_var in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'POSTGRES_HOST', 'POSTGRES_PORT']:
                if f'%({env_var})s' in value:
                    value = value.replace(f'%({env_var})s', getattr(settings, env_var.lower()))
            configuration[key] = value
    
    # Update the configuration with environment variables
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()