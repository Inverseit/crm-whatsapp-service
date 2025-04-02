from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import phonenumbers

from app.db.connection import db
from app.models.conversation import Conversation, ConversationCreate, ConversationUpdate, ConversationState, MessagingPlatform

class ConversationRepository:
    """Repository for conversation data access operations."""
    
    @staticmethod
    async def create(conversation: ConversationCreate) -> Conversation:
        """Create a new conversation in the database."""
        query = """
        INSERT INTO conversation (
            id, phone_number, whatsapp_id, telegram_id, telegram_chat_id, 
            primary_platform, state, is_complete
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8
        ) RETURNING *
        """
        
        # Normalize phone number if provided
        phone_number = conversation.phone_number
        if phone_number:
            try:
                parsed_number = phonenumbers.parse(phone_number, "KZ")
                if phonenumbers.is_valid_number(parsed_number):
                    phone_number = phonenumbers.format_number(
                        parsed_number, phonenumbers.PhoneNumberFormat.E164
                    )
            except Exception:
                pass  # Use the original number if parsing fails
        
        # Set WhatsApp ID to phone number if not provided
        whatsapp_id = conversation.whatsapp_id
        if not whatsapp_id and conversation.primary_platform == MessagingPlatform.WHATSAPP:
            whatsapp_id = phone_number
        
        conversation_id = uuid4()
        values = (
            conversation_id,
            phone_number,
            whatsapp_id,
            conversation.telegram_id,
            conversation.telegram_chat_id,
            conversation.primary_platform.value,
            conversation.state.value,
            conversation.is_complete
        )
        
        row = await db.fetchrow(query, *values)
        return Conversation.model_validate(row)
    
    @staticmethod
    async def get_by_id(conversation_id: UUID) -> Optional[Conversation]:
        """Get a conversation by its ID."""
        query = "SELECT * FROM conversation WHERE id = $1"
        row = await db.fetchrow(query, conversation_id)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_phone(phone_number: str) -> Optional[Conversation]:
        """Get a conversation by phone number."""
        # Try to normalize the phone number for lookup
        try:
            parsed_number = phonenumbers.parse(phone_number, "KZ")
            if phonenumbers.is_valid_number(parsed_number):
                normalized_phone = phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
                
                query = "SELECT * FROM conversation WHERE phone_number = $1"
                row = await db.fetchrow(query, normalized_phone)
                if row:
                    return Conversation.model_validate(row)
        except Exception:
            pass  # If parsing fails, try with the original number
            
        # Try with the original number
        query = "SELECT * FROM conversation WHERE phone_number = $1"
        row = await db.fetchrow(query, phone_number)
        if row:
            return Conversation.model_validate(row)
            
        return None
    
    @staticmethod
    async def get_by_whatsapp_id(whatsapp_id: str) -> Optional[Conversation]:
        """Get a conversation by WhatsApp ID."""
        query = "SELECT * FROM conversation WHERE whatsapp_id = $1"
        row = await db.fetchrow(query, whatsapp_id)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_telegram_id(telegram_id: str) -> Optional[Conversation]:
        """Get a conversation by Telegram user ID."""
        query = "SELECT * FROM conversation WHERE telegram_id = $1"
        row = await db.fetchrow(query, telegram_id)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_telegram_chat_id(telegram_chat_id: str) -> Optional[Conversation]:
        """Get a conversation by Telegram chat ID."""
        query = "SELECT * FROM conversation WHERE telegram_chat_id = $1"
        row = await db.fetchrow(query, telegram_chat_id)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def get_all() -> List[Conversation]:
        """Get all conversations."""
        query = "SELECT * FROM conversation ORDER BY last_updated DESC"
        rows = await db.fetch(query)
        return [Conversation.model_validate(row) for row in rows]
    
    @staticmethod
    async def update(conversation_id: UUID, conversation_update: ConversationUpdate | dict) -> Optional[Conversation]:
        """Update a conversation."""
        # First check if conversation exists
        conversation = await ConversationRepository.get_by_id(conversation_id)
        if not conversation:
            return None
        
        # Build update query dynamically based on provided fields
        update_parts = []
        values = [conversation_id]  # First parameter is always the conversation ID
        param_idx = 2  # Start parameter index at 2
        
        # For each field in the update model, add it to the query if it's not None
        if isinstance(conversation_update, dict):
            conversation_update = ConversationUpdate(**conversation_update)
        fields = conversation_update.model_dump(exclude_none=True)
        for field_name, value in fields.items():
            # Handle enum values
            if isinstance(value, (ConversationState, MessagingPlatform)):
                value = value.value
                
            update_parts.append(f"{field_name} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        # If there are no fields to update, return the original conversation
        if not update_parts:
            return conversation
        
        # Build the complete query
        update_clause = ", ".join(update_parts)
        query = f"UPDATE conversation SET {update_clause}, last_updated = NOW() WHERE id = $1 RETURNING *"
        
        # Execute update
        row = await db.fetchrow(query, *values)
        if row:
            return Conversation.model_validate(row)
        return None
    
    @staticmethod
    async def delete(conversation_id: UUID) -> bool:
        """Delete a conversation."""
        query = "DELETE FROM conversation WHERE id = $1 RETURNING id"
        result = await db.fetchval(query, conversation_id)
        return result is not None
    
    @staticmethod
    async def get_active_conversations() -> List[Conversation]:
        """Get all active (incomplete) conversations."""
        query = "SELECT * FROM conversation WHERE is_complete = FALSE ORDER BY last_updated DESC"
        rows = await db.fetch(query)
        return [Conversation.model_validate(row) for row in rows]
    
    @staticmethod
    async def find_or_create_conversation(
        platform: MessagingPlatform,
        contact_info: Dict[str, str]
    ) -> Conversation:
        """
        Find an existing conversation by platform-specific identifiers or create a new one.
        
        Args:
            platform: The messaging platform
            contact_info: Dictionary with platform-specific identifiers
                (phone_number, whatsapp_id, telegram_id, telegram_chat_id)
                
        Returns:
            An existing or new conversation
        """
        conversation = None
        
        # Try to find conversation based on platform
        if platform == MessagingPlatform.WHATSAPP:
            # For WhatsApp, try to find by WhatsApp ID or phone number
            whatsapp_id = contact_info.get("whatsapp_id", "")
            phone_number = contact_info.get("phone_number", "")
            
            if whatsapp_id:
                conversation = await ConversationRepository.get_by_whatsapp_id(whatsapp_id)
            
            if not conversation and phone_number:
                conversation = await ConversationRepository.get_by_phone(phone_number)
                
        elif platform == MessagingPlatform.TELEGRAM:
            # For Telegram, try to find by chat ID or user ID
            telegram_chat_id = contact_info.get("telegram_chat_id", "")
            telegram_id = contact_info.get("telegram_id", "")
            
            if telegram_chat_id:
                conversation = await ConversationRepository.get_by_telegram_chat_id(telegram_chat_id)
            
            if not conversation and telegram_id:
                conversation = await ConversationRepository.get_by_telegram_id(telegram_id)
        
        # If conversation not found, create a new one
        if not conversation:
            # Create new conversation
            new_conversation = ConversationCreate(
                phone_number=contact_info.get("phone_number", ""),
                whatsapp_id=contact_info.get("whatsapp_id", ""),
                telegram_id=contact_info.get("telegram_id", ""),
                telegram_chat_id=contact_info.get("telegram_chat_id", ""),
                primary_platform=platform
            )
            conversation = await ConversationRepository.create(new_conversation)
        
        # Update missing fields if needed
        update_fields = {}
        
        # Determine which fields need to be updated
        if platform == MessagingPlatform.WHATSAPP:
            if contact_info.get("whatsapp_id") and not conversation.whatsapp_id:
                update_fields["whatsapp_id"] = contact_info["whatsapp_id"]
            if contact_info.get("phone_number") and not conversation.phone_number:
                update_fields["phone_number"] = contact_info["phone_number"]
        
        elif platform == MessagingPlatform.TELEGRAM:
            if contact_info.get("telegram_id") and not conversation.telegram_id:
                update_fields["telegram_id"] = contact_info["telegram_id"]
            if contact_info.get("telegram_chat_id") and not conversation.telegram_chat_id:
                update_fields["telegram_chat_id"] = contact_info["telegram_chat_id"]
        
        # Update the conversation with any new information
        if update_fields:
            conversation = await ConversationRepository.update(conversation.id, update_fields)
        
        return conversation