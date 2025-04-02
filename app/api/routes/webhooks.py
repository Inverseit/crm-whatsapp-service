from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query, Header
from fastapi.responses import JSONResponse, PlainTextResponse
import logging
from typing import Dict, Any, Optional, List
import json

from app.models.message import WebhookMessage
from app.models.conversation import MessagingPlatform
from app.services.booking_service import BookingManager
from app.services.messaging.factory import MessagingFactory
from app.services.messaging.interfaces import TextMessageContent, TemplateMessageContent
from app.api.dependencies import get_booking_manager
from app.config import settings
from app.services.messaging.interfaces import MessageType, UserMessageResponseText, UserMessageResponseTemplate

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
    response_description="Acknowledgment of receipt",
    responses={
        200: {
            "description": "Message received and processing started",
            "content": {
                "application/json": {
                    "example": {"status": "success", "message": "Message received"}
                }
            }
        },
        500: {
            "description": "Error processing the webhook",
            "content": {
                "application/json": {
                    "example": {"status": "error", "message": "Error message details"}
                }
            }
        }
    }
)
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: Optional[str] = Header(None, description="The SHA1 signature of the request payload"),
    booking_manager: BookingManager = Depends(get_booking_manager)
) -> JSONResponse:
    """
    Receive a webhook from WhatsApp.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        x_hub_signature: The SHA1 signature of the request payload (optional)
        booking_manager: The booking manager service
        
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
            parsed_message["phone_number"],
            parsed_message["message"]
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
    response_description="Returns a success message if verification is successful",
    responses={
        200: {
            "description": "Successful verification",
            "content": {
                "application/json": {
                    "example": {"status": "success", "message": "Telegram webhook is operational"}
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
    response_description="Acknowledgment of receipt",
    responses={
        200: {
            "description": "Message received and processing started",
            "content": {
                "application/json": {
                    "example": {"status": "success", "message": "Message received"}
                }
            }
        },
        500: {
            "description": "Error processing the webhook",
            "content": {
                "application/json": {
                    "example": {"status": "error", "message": "Error message details"}
                }
            }
        }
    }
)
async def receive_telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager)
) -> JSONResponse:
    """
    Receive a webhook from Telegram.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        booking_manager: The booking manager service
        
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

@router.post("/message", 
    summary="Receive Generic Message",
    description="""
    Generic webhook endpoint for receiving messages from any messaging platform.
    This can be used with custom integrations where you control the message format.
    """,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Message received and processing started",
            "content": {
                "application/json": {
                    "example": {"status": "success", "message": "Message received"}
                }
            }
        },
        500: {
            "description": "Error processing the message",
            "content": {
                "application/json": {
                    "example": {"status": "error", "message": "Error details"}
                }
            }
        }
    }
)
async def receive_generic_message(
    message: WebhookMessage,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager)
) -> JSONResponse:
    """
    Generic endpoint for receiving messages from any platform.
    
    Args:
        message: The parsed message object
        background_tasks: FastAPI background tasks
        booking_manager: The booking manager service
        
    Returns:
        A JSON response
    """
    try:
        # Create contact info dictionary based on the provided fields
        contact_info = {
            "phone_number": message.phone_number,
            "whatsapp_id": message.whatsapp_id,
            "telegram_id": message.telegram_id,
            "telegram_chat_id": message.telegram_chat_id
        }
        
        # Process the message in the background
        background_tasks.add_task(
            process_generic_message,
            booking_manager,
            contact_info,
            message.message,
            message.platform
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Message received"}
        )
    
    except Exception as e:
        logger.error(f"Error processing generic message: {e}")
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
    responses={
        200: {
            "description": "Test successful",
            "content": {
                "application/json": {
                    "example": {"status": "success", "message": "Test webhook received"}
                }
            }
        }
    }
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
    phone_number: str,
    message: str
) -> None:
    """
    Process a WhatsApp message in the background and send a response.
    
    Args:
        booking_manager: The booking manager service
        phone_number: The sender's phone number
        message: The message content
    """
    try:
        logger.debug(f"Processing WhatsApp message: phone={phone_number}, message={message}")
        
        # Create contact info dictionary for the platform
        contact_info = {
            "phone_number": phone_number,
            "whatsapp_id": phone_number
        }
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            contact_info=contact_info,
            message_text=message,
            platform=MessagingPlatform.WHATSAPP
        )
        
        logger.info(f"Processed WhatsApp message from {phone_number}, response: {response}...")
        
        # Send the response back to the user via WhatsApp
        if should_send:
            task = None
            try:
                if isinstance(response, UserMessageResponseText):
                    # Send a text message
                    logger.info(f"Sending text response to {phone_number}")
                    text_response = response
                    task = booking_manager.send_text_response(phone_number, text_response.text, "whatsapp")
                elif isinstance(response, UserMessageResponseTemplate):
                    # Send a template message
                    logger.info(f"Sending template response to {phone_number}")
                    template_response = response
                    task = booking_manager.send_response_template(
                        phone_number, 
                        template_response.template_name,
                        template_response.template_data, 
                        "whatsapp"
                    )
                else:
                    logger.warning(f"Unsupported message type: {type(response)}")
                    # Fallback to string representation
                    task = booking_manager.send_text_response(phone_number, str(response), "whatsapp")
            except Exception as e:
                logger.error(f"Error sending WhatsApp response: {e}")
                if isinstance(response, str):
                    logger.info(f"FALLBACK: Sending text response to {phone_number}")
                    task = booking_manager.send_text_response(phone_number, response, "whatsapp")
            
            if task:
                success = await task
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
        sender_id = parsed_message.get("sender_id", "")
        chat_id = parsed_message.get("chat_id", "")
        message = parsed_message.get("message", "")
        
        # Create contact info dictionary for the platform
        contact_info = {
            "telegram_id": sender_id,
            "telegram_chat_id": chat_id
        }
        
        logger.debug(f"Processing Telegram message: sender={sender_id}, chat={chat_id}, message={message}")
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            contact_info=contact_info,
            message_text=message,
            platform=MessagingPlatform.TELEGRAM
        )
        
        logger.info(f"Processed Telegram message from {sender_id}, response: {response}...")
        
        # Send the response back to the user via Telegram
        if should_send:
            # Use chat_id as the recipient ID for Telegram messages
            recipient_id = chat_id
            
            task = None
            try:
                if isinstance(response, UserMessageResponseText):
                    # Send a text message
                    logger.info(f"Sending text response to Telegram chat {recipient_id}")
                    text_response = response
                    task = booking_manager.send_text_response(recipient_id, text_response.text, "telegram")
                elif isinstance(response, UserMessageResponseTemplate):
                    # Send a template message (converted to text for Telegram)
                    logger.info(f"Sending template response to Telegram chat {recipient_id}")
                    template_response = response
                    task = booking_manager.send_response_template(
                        recipient_id, 
                        template_response.template_name,
                        template_response.template_data, 
                        "telegram"
                    )
                else:
                    # Fallback to string representation
                    task = booking_manager.send_text_response(recipient_id, str(response), "telegram")
            except Exception as e:
                logger.error(f"Error sending Telegram response: {e}")
                # Fallback to simple text
                if isinstance(response, str):
                    logger.info(f"FALLBACK: Sending text response to Telegram chat {recipient_id}")
                    task = booking_manager.send_text_response(recipient_id, response, "telegram")
            
            if task:
                success = await task
                if success:
                    logger.info(f"Sent Telegram response to chat {recipient_id}")
                else:
                    logger.error(f"Failed to send Telegram response to chat {recipient_id}")
        
    except Exception as e:
        logger.error(f"Error processing Telegram message in background: {e}", exc_info=True)

async def process_generic_message(
    booking_manager: BookingManager,
    contact_info: Dict[str, str],
    message: str,
    platform: MessagingPlatform = MessagingPlatform.GENERIC
) -> None:
    """
    Process a generic message in the background.
    
    Args:
        booking_manager: The booking manager service
        contact_info: Dictionary with contact information
        message: The message content
        platform: The messaging platform
    """
    try:
        logger.debug(f"Processing {platform.value} message: {message}")
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            contact_info=contact_info,
            message_text=message,
            platform=platform
        )
        
        logger.info(f"Processed {platform.value} message, response: {response}...")
        
        # For generic messages, we don't automatically send responses
        # The caller is responsible for retrieving and sending responses
        
    except Exception as e:
        logger.error(f"Error processing {platform.value} message: {e}")

# Original process_message function for backward compatibility
async def process_message(
    booking_manager: BookingManager,
    phone_number: str,
    message: str
) -> None:
    """
    Process a message in the background but don't send a response (legacy method).
    
    Args:
        booking_manager: The booking manager service
        phone_number: The sender's phone number
        message: The message content
    """
    try:
        # Convert to new format
        contact_info = {"phone_number": phone_number, "whatsapp_id": phone_number}
        
        # Process the message with the booking manager
        response, _ = await booking_manager.process_user_message(
            contact_info=contact_info,
            message_text=message,
            platform=MessagingPlatform.WHATSAPP
        )
        logger.info(f"Processed message from {phone_number}, response: {response}...")
        
    except Exception as e:
        logger.error(f"Error processing message in background: {e}")