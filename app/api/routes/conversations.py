from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.message import MessageRepository
from app.models.conversation import Conversation, ConversationUpdate, ConversationState
from app.models.message import Message

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("/", response_model=List[Conversation])
async def get_conversations(
    active_only: bool = Query(False, description="Get only active conversations")
) -> List[Conversation]:
    """
    Get all conversations, optionally filtering for active ones.
    
    Args:
        active_only: If True, only return active (incomplete) conversations
        
    Returns:
        A list of conversations
    """
    if active_only:
        return await ConversationRepository.get_active_conversations()
    else:
        return await ConversationRepository.get_all()

@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: UUID) -> Conversation:
    """
    Get a conversation by ID.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        The conversation, if found
    """
    conversation = await ConversationRepository.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.get("/phone/{phone_number}", response_model=Optional[Conversation])
async def get_conversation_by_phone(phone_number: str) -> Optional[Conversation]:
    """
    Get a conversation by phone number.
    
    Args:
        phone_number: The phone number
        
    Returns:
        The conversation, if found
    """
    conversation = await ConversationRepository.get_by_phone(phone_number)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.put("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID, 
    conversation_update: ConversationUpdate
) -> Conversation:
    """
    Update a conversation.
    
    Args:
        conversation_id: The conversation ID
        conversation_update: The conversation update data
        
    Returns:
        The updated conversation
    """
    conversation = await ConversationRepository.update(conversation_id, conversation_update)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: UUID) -> dict:
    """
    Delete a conversation.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        A success message
    """
    success = await ConversationRepository.delete(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": "Conversation deleted"}

@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(100, description="Max number of messages to return"),
    offset: int = Query(0, description="Number of messages to skip")
) -> List[Message]:
    """
    Get messages for a conversation.
    
    Args:
        conversation_id: The conversation ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        
    Returns:
        A list of messages
    """
    # First check if conversation exists
    conversation = await ConversationRepository.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return await MessageRepository.get_by_conversation(conversation_id, limit, offset)

@router.get("/{conversation_id}/history", response_model=List[Message])
async def get_conversation_history(conversation_id: UUID) -> List[Message]:
    """
    Get the full conversation history in chronological order.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        A list of messages in chronological order
    """
    # First check if conversation exists
    conversation = await ConversationRepository.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return await MessageRepository.get_conversation_history(conversation_id)

@router.post("/{conversation_id}/reset")
async def reset_conversation(conversation_id: UUID) -> dict:
    """
    Reset a conversation to the greeting state.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        A success message
    """
    # First check if conversation exists
    conversation = await ConversationRepository.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Update conversation state
    await ConversationRepository.update(
        conversation_id,
        {"state": ConversationState.GREETING, "is_complete": False}
    )
    
    # Delete all messages (optional, can be commented out if you want to keep the history)
    await MessageRepository.delete_by_conversation(conversation_id)
    
    return {"status": "success", "message": "Conversation reset"}