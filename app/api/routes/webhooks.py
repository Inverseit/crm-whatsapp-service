from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from app.models.message import WebhookMessage
from app.services.booking_service import BookingManager
from app.api.dependencies import get_booking_manager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

@router.post("/message")
async def receive_message(
    webhook: WebhookMessage,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager)
) -> JSONResponse:
    """
    Receive a message from a messaging service webhook.
    
    Args:
        webhook: The webhook message
        background_tasks: FastAPI background tasks
        booking_manager: The booking manager service
        
    Returns:
        A JSON response
    """
    try:
        # Log the incoming webhook
        logger.info(f"Received webhook message from {webhook.phone_number}: {webhook.message}")
        
        # Process the message in the background
        background_tasks.add_task(
            process_message,
            booking_manager,
            webhook.phone_number,
            webhook.message
        )
        
        # Return immediate success to the webhook caller
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Message received"}
        )
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

async def process_message(
    booking_manager: BookingManager,
    phone_number: str,
    message: str
) -> None:
    """
    Process a message in the background.
    
    Args:
        booking_manager: The booking manager service
        phone_number: The sender's phone number
        message: The message content
    """
    try:
        # Process the message with the booking manager
        response = await booking_manager.process_user_message(phone_number, message)
        logger.info(f"Processed message from {phone_number}, response: {response[:50]}...")
        
        # Here you would typically send the response back to the user
        # via the messaging service API (WhatsApp, Telegram, etc.)
        # This part is not implemented here as it depends on the specific
        # messaging service being used
        
    except Exception as e:
        logger.error(f"Error processing message in background: {e}")