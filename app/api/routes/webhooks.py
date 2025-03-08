from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
import logging
from typing import Dict, Any, Optional
import json

from app.models.message import WebhookMessage
from app.services.booking_service import BookingManager
from app.services.whatsapp_service import WhatsAppService
from app.api.dependencies import get_booking_manager, get_whatsapp_service
from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    mode: str = Query(...),
    token: str = Query(...),
    challenge: str = Query(...),
) -> PlainTextResponse:
    """
    Handle WhatsApp webhook verification.
    
    Args:
        mode: The hub mode
        token: The verification token
        challenge: The challenge string
        
    Returns:
        The challenge string if verification succeeds
    """
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified")
        return PlainTextResponse(content=challenge)
    else:
        logger.warning("WhatsApp webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service)
) -> JSONResponse:
    """
    Receive a webhook from WhatsApp.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
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

@router.post("/message")
async def receive_message(
    webhook: WebhookMessage,
    background_tasks: BackgroundTasks,
    booking_manager: BookingManager = Depends(get_booking_manager)
) -> JSONResponse:
    """
    Receive a message from a generic messaging service webhook.
    
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
        # Process the message with the booking manager
        response, should_send = await booking_manager.process_user_message(phone_number, message)
        logger.info(f"Processed WhatsApp message from {phone_number}, response: {response[:50]}...")
        
        # Send the response back to the user via WhatsApp
        if should_send:
            success = await booking_manager.send_response(phone_number, response)
            if success:
                logger.info(f"Sent WhatsApp response to {phone_number}")
            else:
                logger.error(f"Failed to send WhatsApp response to {phone_number}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message in background: {e}")

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
        logger.info(f"Processed message from {phone_number}, response: {response[:50]}...")
        
        # Here you would typically integrate with your messaging platform to send the response
        
    except Exception as e:
        logger.error(f"Error processing message in background: {e}")