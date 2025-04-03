from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query, Header
from fastapi.responses import JSONResponse, PlainTextResponse
import logging
from typing import Dict, Any, Optional, List
import json

from app.models.message import WebhookMessage
from app.services.booking_service import BookingManager
from app.services.messaging.factory import MessagingFactory
from app.api.dependencies import get_booking_manager, get_db
from app.config import settings
from app.services.messaging.interfaces import MessageType, UserMessageResponseText, UserMessageResponseTemplate
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

@router.get("/whatsapp", 
    summary="Verify WhatsApp Webhook",
    description="""
    Handles the webhook verification request from Meta/WhatsApp.
    This endpoint is called by Meta when you set up your webhook in the Meta developer portal.
    """,
    response_description="Returns the challenge string if verification is successful",
    responses={
    200: {
        "description": "Successful verification",
        "content": {
            "text/plain": {
                "example": "1234567890"
            }
        }
    },
    403: {
        "description": "Verification failed",
        "content": {
            "application/json": {
                "example": {"detail": "Verification failed"}
            }
        }
    }
    }
)
async def verify_whatsapp_webhook(
    request: Request,
) -> PlainTextResponse:
    """
    Handle WhatsApp webhook verification with proper hub.* parameters.
    
    Args:
        request: The HTTP request containing hub.mode, hub.challenge, and hub.verify_token
        
    Returns:
        The challenge string if verification succeeds
    """
    # Extract query parameters
    query_params = dict(request.query_params)
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token")
    challenge = query_params.get("hub.challenge")
    
    logger.info(f"Received verification request: mode={mode}, token={token}, challenge={challenge}")
    
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        if challenge:
            return PlainTextResponse(content=challenge)
        else:
            logger.warning("Challenge parameter missing in verification request")
            return PlainTextResponse(content="Challenge parameter missing", status_code=400)
    else:
        logger.warning("WhatsApp webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp", 
    summary="Receive WhatsApp Messages",
    description="""
    Receives webhook notifications from WhatsApp when a user sends a message.
    Processes the message and sends a response back to the user via the WhatsApp API.
    
    This endpoint expects the format from the WhatsApp Business API/Meta Cloud API.
    """,
    response_description="Acknowledgment of receipt"
)
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: Optional[str] = Header(None, description="The SHA1 signature of the request payload"),
    booking_manager: BookingManager = Depends(get_booking_manager),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Receive a webhook from WhatsApp.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        x_hub_signature: The SHA1 signature of the request payload (optional)
        booking_manager: The booking manager service
        db: The database session
        
    Returns:
        A JSON response
    """
    try:
        # Parse request body
        data = await request.json()
        logger.debug(f"Received WhatsApp webhook: {data}")
        
        # Get WhatsApp transport
        whatsapp_transport = MessagingFactory.get_transport("whatsapp")
        if not whatsapp_transport:
            logger.error("WhatsApp transport not available")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "WhatsApp transport not available"}
            )
            
        # Parse the webhook data
        parsed_message = await whatsapp_transport.parse_webhook(data)
        
        if not parsed_message:
            logger.info("No valid message in webhook")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "No valid message found"}
            )
        
        # Process the message in the background
        background_tasks.add_task(
            process_whatsapp_message,
            booking_manager,
            parsed_message
        )
        
        # Return immediate success to WhatsApp
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Message received"}
        )
    
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@router.get("/telegram", 
    summary="Verify Telegram Webhook",
    description="""
    Handles the webhook verification request from Telegram.
    This endpoint can be used to check if the webhook is properly set up.
    """,
    response_description="Returns a success message if verification is successful"
)
async def verify_telegram_webhook(
    request: Request,
    token: str = Query(None, description="Verification token")
) -> JSONResponse:
    """
    Handle Telegram webhook verification.
    
    Args:
        request: The HTTP request
        token: Verification token
        
    Returns:
        Success message if verification succeeds
    """
    if token and token == settings.telegram_webhook_token:
        logger.info("Telegram webhook verified successfully")
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Telegram webhook is operational"}
        )
    else:
        logger.warning("Telegram webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/telegram", 
    summary="Receive Telegram Messages",
    description="""
    Receives webhook notifications from Telegram when a user sends a message.
    Processes the message and sends a response back to the user via the Telegram Bot API.
    
    This endpoint expects the format from the Telegram Bot API.
    """,
    response_description="Acknowledgment of receipt"
)
async def receive_telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Receive a webhook from Telegram.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        booking_manager: The booking manager service
        db: The database session
        
    Returns:
        A JSON response
    """
    try:
        # Parse request body
        data = await request.json()
        logger.debug(f"Received Telegram webhook: {data}")
        
        # Get Telegram transport
        telegram_transport = MessagingFactory.get_transport("telegram")
        if not telegram_transport:
            logger.error("Telegram transport not available")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Telegram transport not available"}
            )
            
        # Parse the webhook data
        parsed_message = await telegram_transport.parse_webhook(data)
        
        if not parsed_message:
            logger.info("No valid message in webhook")
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "No valid message found"}
            )
        
        # Process the message in the background
        background_tasks.add_task(
            process_telegram_message,
            booking_manager,
            parsed_message
        )
        
        # Return immediate success to Telegram
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Message received"}
        )
    
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@router.get("/test", 
    summary="Test Webhook Processing",
    description="""
    Test endpoint for webhook processing without actually sending messages.
    Useful for development and testing.
    """,
    response_description="Test successful"
)
async def test_webhook() -> JSONResponse:
    """Test endpoint for webhook functionality."""
    logger.info("Test webhook endpoint called")
    return JSONResponse(
        status_code=200, 
        content={"status": "success", "message": "Test webhook received"}
    )

async def process_whatsapp_message(
    booking_manager: BookingManager,
    parsed_message: Dict[str, Any]
) -> None:
    """
    Process a WhatsApp message in the background and send a response.
    
    Args:
        booking_manager: The booking manager service
        parsed_message: The parsed message data
    """
    try:
        phone_number = parsed_message.get("phone_number", "")
        whatsapp_id = parsed_message.get("sender_id", "")
        message_text = parsed_message.get("message", "")
        profile_name = parsed_message.get("profile_name", "")
        
        logger.debug(f"Processing WhatsApp message: phone={phone_number}, whatsapp_id={whatsapp_id}, message={message_text}")
        
        # Create contact info dictionary for the platform
        contact_info = {
            "phone_number": phone_number,
            "whatsapp_id": whatsapp_id,
            "profile_name": profile_name
        }
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            platform="whatsapp",
            user_contact_info=contact_info,
            message_text=message_text
        )
        
        logger.info(f"Processed WhatsApp message from {phone_number}, response ready: {should_send}")
        
        # Send the response back to the user via WhatsApp
        if should_send:
            success = await booking_manager.send_message("whatsapp", whatsapp_id, response)
            if success:
                logger.info(f"Sent WhatsApp response to {phone_number}")
            else:
                logger.error(f"Failed to send WhatsApp response to {phone_number}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message in background: {e}", exc_info=True)

async def process_telegram_message(
    booking_manager: BookingManager,
    parsed_message: Dict[str, Any]
) -> None:
    """
    Process a Telegram message in the background and send a response.
    
    Args:
        booking_manager: The booking manager service
        parsed_message: The parsed message data
    """
    try:
        telegram_id = parsed_message.get("sender_id", "")
        chat_id = parsed_message.get("chat_id", "")
        message_text = parsed_message.get("message", "")
        first_name = parsed_message.get("first_name", "")
        last_name = parsed_message.get("last_name", "")
        username = parsed_message.get("username", "")
        
        logger.debug(f"Processing Telegram message: sender={telegram_id}, chat={chat_id}, message={message_text}")
        
        # Create contact info dictionary for the platform
        contact_info = {
            "telegram_id": telegram_id,
            "chat_id": chat_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username
        }
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            platform="telegram",
            user_contact_info=contact_info,
            message_text=message_text
        )
        
        logger.info(f"Processed Telegram message from {telegram_id}, response ready: {should_send}")
        
        # Send the response back to the user via Telegram
        if should_send:
            # Use chat_id as the recipient ID for Telegram messages
            recipient_id = chat_id
            
            success = await booking_manager.send_message("telegram", recipient_id, response)
            if success:
                logger.info(f"Sent Telegram response to chat {recipient_id}")
            else:
                logger.error(f"Failed to send Telegram response to chat {recipient_id}")
        
    except Exception as e:
        logger.error(f"Error processing Telegram message in background: {e}", exc_info=True)