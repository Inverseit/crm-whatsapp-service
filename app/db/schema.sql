-- Drop tables if they exist (useful for development)
DROP TABLE IF EXISTS message CASCADE;
DROP TABLE IF EXISTS booking CASCADE;
DROP TABLE IF EXISTS conversation CASCADE;

-- Create enum types
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_type') THEN
    CREATE TYPE message_type AS ENUM ('text', 'image', 'document', 'location');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'time_of_day') THEN
    CREATE TYPE time_of_day AS ENUM ('morning', 'afternoon', 'evening');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'contact_method') THEN
    CREATE TYPE contact_method AS ENUM ('phone_call', 'whatsapp_message');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status') THEN
    CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'cancelled');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'conversation_state') THEN
    CREATE TYPE conversation_state AS ENUM ('greeting', 'collecting_info', 'confirming', 'completed');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'messaging_platform') THEN
    CREATE TYPE messaging_platform AS ENUM ('whatsapp', 'telegram', 'generic');
  END IF;
END $$;

-- Create conversations table
CREATE TABLE conversation (
    id UUID PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL DEFAULT '',
    whatsapp_id VARCHAR(20) NOT NULL DEFAULT '',
    telegram_id VARCHAR(20) NOT NULL DEFAULT '',
    telegram_chat_id VARCHAR(20) NOT NULL DEFAULT '',
    primary_platform messaging_platform NOT NULL DEFAULT 'whatsapp',
    state conversation_state NOT NULL DEFAULT 'greeting',
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes on various fields for faster lookups
CREATE INDEX idx_conversation_phone ON conversation(phone_number);
CREATE INDEX idx_conversation_whatsapp ON conversation(whatsapp_id);
CREATE INDEX idx_conversation_telegram_id ON conversation(telegram_id);
CREATE INDEX idx_conversation_telegram_chat ON conversation(telegram_chat_id);
CREATE INDEX idx_conversation_platform ON conversation(primary_platform);

-- Create bookings table
CREATE TABLE booking (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversation(id),
    client_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    use_phone_for_whatsapp BOOLEAN NOT NULL DEFAULT TRUE,
    whatsapp VARCHAR(20),
    preferred_contact_method contact_method NOT NULL,
    preferred_contact_time time_of_day,
    service_description TEXT NOT NULL,
    booking_date DATE,
    booking_time TIME,
    time_of_day time_of_day,
    additional_notes TEXT,
    status booking_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index on conversation_id for faster lookups
CREATE INDEX idx_booking_conversation ON booking(conversation_id);

-- Create messages table
CREATE TABLE message (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversation(id),
    content TEXT NOT NULL,
    message_type message_type NOT NULL DEFAULT 'text',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sender_id VARCHAR(255) NOT NULL,
    is_from_bot BOOLEAN NOT NULL DEFAULT FALSE,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    platform messaging_platform NOT NULL DEFAULT 'whatsapp'
);

-- Create index on conversation_id and timestamp for faster message history retrieval
CREATE INDEX idx_message_conversation_time ON message(conversation_id, timestamp);
CREATE INDEX idx_message_platform ON message(platform);

-- Function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to update last_updated on rows
CREATE TRIGGER update_conversation_last_updated
BEFORE UPDATE ON conversation
FOR EACH ROW EXECUTE FUNCTION update_last_updated_column();

CREATE TRIGGER update_booking_last_updated
BEFORE UPDATE ON booking
FOR EACH ROW EXECUTE FUNCTION update_last_updated_column();