import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID
from datetime import datetime, date, time
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.booking_repository import BookingRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.user_repository import TelegramUserRepository, WhatsAppUserRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.models import (
    Booking, ConversationState, TimeOfDay, ContactMethod, 
    BookingStatus, TelegramUser, WhatsAppUser, Conversation, Message
)
from app.services.gpt_service import GPTService
from app.services.platform_handler import get_platform_handler
from app.services.messaging.interfaces import (
    UserMessageResponseBase, UserMessageResponseText, UserMessageResponseTemplate
)
from app.services.notification_service import NotificationClient

logger = logging.getLogger(__name__)

class BookingManager:
    """Manager for booking-related operations with SQLAlchemy."""

    def __init__(
        self,
        db_session: AsyncSession,
        gpt_service: GPTService,
    ):
        self.db_session = db_session
        self.gpt_service = gpt_service

    async def process_user_message(
        self, 
        platform: str,
        user_contact_info: Dict[str, str], 
        message_text: str,
    ) -> Tuple[UserMessageResponseBase, bool]:
        """
        Process a user message and update the conversation state accordingly.

        Args:
            platform: The messaging platform (telegram, whatsapp)
            user_contact_info: Dict containing platform-specific contact information
            message_text: The message content

        Returns:
            Tuple of (response_message, should_send_response)
        """
        # Get the appropriate platform handler
        handler = get_platform_handler(platform, self.db_session, self.gpt_service)
        
        # Process the message using the platform-specific handler
        response, should_send = await handler.process_message(user_contact_info, message_text)
        
        return response, should_send

    async def create_booking_from_data(
        self,
        conversation_id: UUID,
        booking_data: Dict[str, Any],
        platform: str
    ) -> Optional[Booking]:
        """
        Create a booking from the collected data.

        Args:
            conversation_id: The conversation ID
            booking_data: The booking data
            platform: The messaging platform

        Returns:
            The created booking or None if failed
        """
        try:
            # Get the conversation
            conversation = await ConversationRepository.get_by_id(self.db_session, conversation_id)
            if not conversation:
                logger.error(f"Conversation not found: {conversation_id}")
                return None
                
            # Parse booking data
            client_name = booking_data.get("client_name", "")
            phone = booking_data.get("phone", "")
            use_phone_for_whatsapp = booking_data.get("use_phone_for_whatsapp", True)
            whatsapp = booking_data.get("whatsapp")
            
            # Handle preferred contact method
            preferred_contact_method_str = booking_data.get("preferred_contact_method", "")
            if preferred_contact_method_str == "telegram_message" and platform == "telegram":
                preferred_contact_method = ContactMethod.TELEGRAM_MESSAGE
            elif preferred_contact_method_str == "whatsapp_message" or (platform == "whatsapp" and not preferred_contact_method_str):
                preferred_contact_method = ContactMethod.WHATSAPP_MESSAGE
            else:
                preferred_contact_method = ContactMethod.PHONE_CALL
            
            # Parse preferred contact time
            preferred_contact_time_str = booking_data.get("preferred_contact_time")
            preferred_contact_time = TimeOfDay(preferred_contact_time_str) if preferred_contact_time_str else None
            
            # Parse service description
            service_description = booking_data.get("service_description", "")
            
            # Parse booking date
            booking_date_str = booking_data.get("booking_date")
            booking_date = None
            if booking_date_str:
                try:
                    date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]
                    for fmt in date_formats:
                        try:
                            booking_date = datetime.strptime(booking_date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.error(f"Error parsing booking date: {e}")
            
            # Parse booking time
            booking_time_str = booking_data.get("booking_time")
            booking_time = None
            if booking_time_str:
                try:
                    time_formats = ["%H:%M", "%H:%M:%S", "%I:%M %p"]
                    for fmt in time_formats:
                        try:
                            booking_time = datetime.strptime(booking_time_str, fmt).time()
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.error(f"Error parsing booking time: {e}")
            
            # Parse time of day
            time_of_day_str = booking_data.get("time_of_day")
            time_of_day = TimeOfDay(time_of_day_str) if time_of_day_str else None
            
            # Parse additional notes
            additional_notes = booking_data.get("additional_notes")
            
            # Create the booking
            booking = await BookingRepository.create(
                self.db_session,
                conversation_id=conversation_id,
                client_name=client_name,
                phone=phone,
                service_description=service_description,
                preferred_contact_method=preferred_contact_method,
                use_phone_for_whatsapp=use_phone_for_whatsapp,
                whatsapp=whatsapp,
                preferred_contact_time=preferred_contact_time,
                booking_date=booking_date,
                booking_time=booking_time,
                time_of_day=time_of_day,
                additional_notes=additional_notes,
                status=BookingStatus.PENDING
            )
            
            # Update conversation state
            await ConversationRepository.update(
                self.db_session,
                conversation_id,
                state=ConversationState.COMPLETED,
                is_complete=True
            )
            
            # Mark messages as complete
            await MessageRepository.mark_conversation_messages_as_complete(self.db_session, conversation_id)
            
            # Send notification to backend
            try:
                notification_data = {
                    "type": "booking",
                    "booking_id": str(booking.id),
                    "phone_number": booking.phone,
                    "client_name": booking.client_name,
                    "service_description": booking.service_description,
                    "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
                    "booking_time": booking.booking_time.isoformat() if booking.booking_time else None,
                    "time_of_day": booking.time_of_day.value if booking.time_of_day else None,
                    "preferred_contact_method": booking.preferred_contact_method.value,
                    "preferred_contact_time": booking.preferred_contact_time.value if booking.preferred_contact_time else None,
                    "additional_notes": booking.additional_notes,
                    "platform": platform
                }
                
                # If it's a Telegram booking, add username
                if platform == "telegram" and conversation.telegram_user_id:
                    telegram_user = await TelegramUserRepository.get_by_id(self.db_session, conversation.telegram_user_id)
                    if telegram_user and telegram_user.username:
                        notification_data["telegram_username"] = telegram_user.username
                
                NotificationClient().create_notification(notification_data)
            except Exception as e:
                logger.error(f"Error creating notification: {e}")
            
            return booking
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}", exc_info=True)
            return None

    async def send_message(
        self, platform: str, recipient_id: str, message: UserMessageResponseBase
    ) -> bool:
        """
        Send a message to a user through the specified platform.

        Args:
            platform: The messaging platform
            recipient_id: The recipient ID
            message: The message to send

        Returns:
            True if sent successfully, False otherwise
        """
        handler = get_platform_handler(platform, self.db_session, self.gpt_service)
        return await handler.send_message(recipient_id, message)