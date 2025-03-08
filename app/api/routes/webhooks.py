from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query, Header
from fastapi.responses import JSONResponse, PlainTextResponse
import logging
from typing import Dict, Any, Optional, List
import json

from app.models.message import WebhookMessage
from app.services.booking_service import BookingManager
from app.services.whatsapp_service import WhatsAppService
from app.api.dependencies import get_booking_manager, get_whatsapp_service
from app.config import settings
from app.services.user_message_responses import MessageType, UserMessageResponseText, UserMessageResponseTemplate

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
    booking_manager: BookingManager = Depends(get_booking_manager),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service)
) -> JSONResponse:
    """
    Receive a webhook from WhatsApp.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        x_hub_signature: The SHA1 signature of the request payload (optional)
        booking_manager: The booking manager service
        whatsapp_service: The WhatsApp service
        
    Returns:
        A JSON response
    """
    try:
        # Parse request body
        data = await request.json()
        logger.debug(f"Received WhatsApp webhook: {data}")
        
        # Parse the webhook data
        parsed_message = await whatsapp_service.parse_webhook(data)
        
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
        
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(
            phone_number=phone_number, 
            message_text=message
        )
        
        logger.info(f"Processed WhatsApp message from {phone_number}, response: {response}...")
        
        # Send the response back to the user via WhatsApp
        if should_send:
            task = None
            try:
              match response.message_type:
                  case MessageType.TEXT:
                      # Send a text message
                      logger.info(f"Sending text response to {phone_number}")
                      text_response: UserMessageResponseText = response
                      task = booking_manager.send_text_response(phone_number,text_response.text)
                  case MessageType.TEMPLATE:
                      # Send a template message
                      logger.info(f"Sending template response to {phone_number}")
                      template_response: UserMessageResponseTemplate = response
                      task = booking_manager.send_response_template(phone_number,template_response.template_name,template_response.template_data)
                  case _:
                      logger.warning("Unsupported message type")
                      return
            except Exception as e:
                logger.error(f"Error sending WhatsApp response: {e}")
                if type(response) is str:
                    logger.info(f"FALLBACK: Sending text response to {phone_number}")
                    task = booking_manager.send_text_response(phone_number, response)
            if task:
                success = await task
                if success:
                    logger.info(f"Sent WhatsApp response to {phone_number}")
                else:
                    logger.error(f"Failed to send WhatsApp response to {phone_number}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message in background: {e}", exc_info=True)

async def process_message(
    booking_manager: BookingManager,
    phone_number: str,
    message: str
) -> None:
    """
    Process a message in the background but don't send a response.
    
    Args:
        booking_manager: The booking manager service
        phone_number: The sender's phone number
        message: The message content
    """
    try:
        # Process the message with the booking manager
        response, _ = await booking_manager.process_user_message(phone_number, message)
        logger.info(f"Processed message from {phone_number}, response: {response}...")
        
        # Here you would typically integrate with your messaging platform to send the response
        
    except Exception as e:
        logger.error(f"Error processing message in background: {e}")