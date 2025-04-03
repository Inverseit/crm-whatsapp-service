"""Initial revision

Revision ID: 0001
Revises: 
Create Date: 2025-04-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def create_enum_if_not_exists(enum_name, enum_values):
    """Safely create an enum type only if it doesn't exist already."""
    # Check if enum type exists
    conn = op.get_bind()
    query = text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name)"
    )
    exists = conn.execute(query, {"enum_name": enum_name}).scalar()
    
    if not exists:
        op.execute(f"CREATE TYPE {enum_name} AS ENUM {enum_values}")


def drop_enum_if_exists(enum_name):
    """Safely drop an enum type only if it exists."""
    conn = op.get_bind()
    query = text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name)"
    )
    exists = conn.execute(query, {"enum_name": enum_name}).scalar()
    
    if exists:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")


def table_exists(table_name):
    """Check if a table exists."""
    conn = op.get_bind()
    insp = inspect(conn)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    # Safely create enum types
    create_enum_if_not_exists('conversation_state', "('greeting', 'collecting_info', 'confirming', 'completed')")
    create_enum_if_not_exists('booking_status', "('pending', 'confirmed', 'cancelled')")
    create_enum_if_not_exists('time_of_day', "('morning', 'afternoon', 'evening')")
    create_enum_if_not_exists('contact_method', "('phone_call', 'whatsapp_message', 'telegram_message')")
    create_enum_if_not_exists('message_type', "('text', 'image', 'document', 'location')")
    
    # Create telegram_user table if it doesn't exist
    if not table_exists('telegram_user'):
        op.create_table('telegram_user',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('telegram_id', sa.String(20), nullable=False, unique=True, index=True),
            sa.Column('chat_id', sa.String(20), nullable=False, index=True),
            sa.Column('username', sa.String(255), nullable=True),
            sa.Column('first_name', sa.String(255), nullable=True),
            sa.Column('last_name', sa.String(255), nullable=True),
            sa.Column('phone_number', sa.String(20), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('is_active', sa.Boolean, default=True, nullable=False)
        )
    
    # Create whatsapp_user table if it doesn't exist
    if not table_exists('whatsapp_user'):
        op.create_table('whatsapp_user',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('phone_number', sa.String(20), nullable=False, unique=True, index=True),
            sa.Column('whatsapp_id', sa.String(20), nullable=False, index=True),
            sa.Column('profile_name', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('is_active', sa.Boolean, default=True, nullable=False)
        )
    
    # Create conversation table if it doesn't exist
    if not table_exists('conversation'):
        op.create_table('conversation',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('state', sa.Enum('greeting', 'collecting_info', 'confirming', 'completed', name='conversation_state'), 
                    nullable=False, server_default='greeting'),
            sa.Column('is_complete', sa.Boolean, default=False, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('telegram_user_id', UUID(as_uuid=True), sa.ForeignKey('telegram_user.id'), nullable=True),
            sa.Column('whatsapp_user_id', UUID(as_uuid=True), sa.ForeignKey('whatsapp_user.id'), nullable=True),
            sa.Column('platform', sa.String(20), nullable=False, index=True)
        )
    
    # Create message table if it doesn't exist
    if not table_exists('message'):
        op.create_table('message',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversation.id'), nullable=False),
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('message_type', sa.Enum('text', 'image', 'document', 'location', name='message_type'), 
                    nullable=False, server_default='text'),
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('sender_id', sa.String(255), nullable=False),
            sa.Column('is_from_bot', sa.Boolean, default=False, nullable=False),
            sa.Column('is_complete', sa.Boolean, default=False, nullable=False)
        )
    
    # Create booking table if it doesn't exist
    if not table_exists('booking'):
        op.create_table('booking',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversation.id'), nullable=False),
            sa.Column('client_name', sa.String(255), nullable=False),
            sa.Column('phone', sa.String(20), nullable=False),
            sa.Column('use_phone_for_whatsapp', sa.Boolean, default=True, nullable=False),
            sa.Column('whatsapp', sa.String(20), nullable=True),
            sa.Column('preferred_contact_method', sa.Enum('phone_call', 'whatsapp_message', 'telegram_message', 
                                                        name='contact_method'), nullable=False),
            sa.Column('preferred_contact_time', sa.Enum('morning', 'afternoon', 'evening', name='time_of_day'), nullable=True),
            sa.Column('service_description', sa.Text, nullable=False),
            sa.Column('booking_date', sa.DateTime, nullable=True),
            sa.Column('booking_time', sa.DateTime, nullable=True),
            sa.Column('time_of_day', sa.Enum('morning', 'afternoon', 'evening', name='time_of_day'), nullable=True),
            sa.Column('additional_notes', sa.Text, nullable=True),
            sa.Column('status', sa.Enum('pending', 'confirmed', 'cancelled', name='booking_status'), 
                    nullable=False, server_default='pending'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
        )
    
        # Create indexes
        op.create_index('idx_conversation_telegram_user', 'conversation', ['telegram_user_id'])
        op.create_index('idx_conversation_whatsapp_user', 'conversation', ['whatsapp_user_id'])
        op.create_index('idx_message_conversation_time', 'message', ['conversation_id', 'timestamp'])
        op.create_index('idx_booking_conversation', 'booking', ['conversation_id'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('booking')
    op.drop_table('message')
    op.drop_table('conversation')
    op.drop_table('telegram_user')
    op.drop_table('whatsapp_user')
    
    # Drop enum types
    for enum_name in ['conversation_state', 'booking_status', 'time_of_day', 'contact_method', 'message_type']:
        drop_enum_if_exists(enum_name)