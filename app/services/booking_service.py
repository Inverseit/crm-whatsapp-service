import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID
from datetime import datetime, date, time

from app.db.repositories.booking import BookingRepository
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.message import MessageRepository
from app.models.booking import (
    Booking,
    BookingCreate,
    BookingStatus,
    TimeOfDay,
    ContactMethod,
    BookingFunctionArgs,
)
from app.models.conversation import Conversation, ConversationState, MessagingPlatform
from app.models.message import Message, MessageCreate, MessageType
from app.services.gpt_service import GPTService
from app.config import settings
from .messaging.interfaces import (
    UserMessageResponseBase,
    UserMessageResponseText,
    UserMessageResponseTemplate,
)
from .notification_service import NotificationClient

logger = logging.getLogger(__name__)

class BookingManager:
    """Manager for booking-related operations."""

    def __init__(
        self,
        gpt_service: Optional[GPTService] = None,
    ):
        self.gpt_service = gpt_service or GPTService()

    async def process_user_message(
        self, 
        contact_info: Dict[str, str], 
        message_text: str,
        platform: MessagingPlatform = MessagingPlatform.WHATSAPP
    ) -> Tuple[UserMessageResponseBase, bool]:
        """
        Process a user message and update the conversation state accordingly.

        Args:
            contact_info: Dict containing platform-specific contact information
                (e.g., phone_number, whatsapp_id, telegram_id, telegram_chat_id)
            message_text: The message content
            platform: The messaging platform the message was received from

        Returns:
            Tuple of (response_message, should_send_response)
        """
        # Find or create conversation for this user
        conversation = await ConversationRepository.find_or_create_conversation(
            platform, contact_info
        )

        # Determine sender ID based on platform
        sender_id = self._get_sender_id(contact_info, platform)

        # Create a message record
        user_message = MessageCreate(
            content=message_text, 
            sender_id=sender_id, 
            is_from_bot=False,
            platform=platform
        )
        await MessageRepository.create(conversation.id, user_message)

        # Process message based on conversation state
        if conversation.state == ConversationState.GREETING:
            logger.debug("Handling greeting state")
            greeting_message = await self._handle_greeting(conversation)
            return (
                UserMessageResponseTemplate(
                    template_name=settings.whatsapp_greeting_template, 
                    template_data={}
                ),
                True,
            )
        elif conversation.state == ConversationState.COMPLETED:
            await ConversationRepository.update(
                conversation.id,
                {"state": ConversationState.GREETING, "is_complete": True},
            )
            greeting_message = await self._handle_greeting(conversation)
            return (
                UserMessageResponseTemplate(
                    template_name=settings.whatsapp_greeting_template, 
                    template_data={}
                ),
                True,
            )
        elif conversation.state == ConversationState.COLLECTING_INFO:
            # For all other states, just process with GPT and check for booking data
            logger.debug("Handling conversation with GPT")
            return await self._handle_conversation_with_gpt(conversation, message_text, platform)
        else:
            logger.warning(f"Unknown conversation state: {conversation.state}")
            return (
                UserMessageResponseText(
                    text="Извините, произошла ошибка. Пожалуйста, попробуйте еще раз."
                ),
                True,
            )

    def _get_sender_id(self, contact_info: Dict[str, str], platform: MessagingPlatform) -> str:
        """
        Get the appropriate sender ID based on platform and available contact info.
        
        Args:
            contact_info: Dict with platform-specific contact information
            platform: The messaging platform
            
        Returns:
            The appropriate sender ID for the platform
        """
        if platform == MessagingPlatform.WHATSAPP:
            return contact_info.get("whatsapp_id", "") or contact_info.get("phone_number", "")
        elif platform == MessagingPlatform.TELEGRAM:
            return contact_info.get("telegram_id", "")
        return contact_info.get("phone_number", "")

    async def _handle_greeting(self, conversation: Conversation) -> str:
        """
        Handle the greeting state of a conversation.

        Args:
            conversation: The conversation

        Returns:
            The response message
        """
        # Update conversation state to in progress
        await ConversationRepository.update(
            conversation.id, {"state": ConversationState.COLLECTING_INFO}
        )

        # Send greeting message
        greeting = "Здравствуйте! Я бот салона красоты. Я помогу вам записаться на процедуру. Подскажите, пожалуйста, как к вам обращаться?"

        # Create a bot message
        bot_message = MessageCreate(
            content=greeting, 
            sender_id="bot", 
            is_from_bot=True,
            platform=conversation.primary_platform
        )
        await MessageRepository.create(conversation.id, bot_message)

        return greeting

    async def _handle_conversation_with_gpt(
        self, conversation: Conversation, message_text: str, platform: MessagingPlatform
    ) -> Tuple[UserMessageResponseBase, bool]:
        """
        Process the conversation with GPT and check for booking data.

        Args:
            conversation: The conversation
            message_text: The user's message
            platform: The messaging platform

        Returns:
            Tuple of (response, should_send)
        """
        # Get the appropriate contact identifier
        contact_id = conversation.get_platform_id(platform)
        
        # Process message with GPT
        response, booking_data = await self.gpt_service.process_message(
            conversation.id, message_text, contact_id, platform
        )

        # If booking data was provided by GPT, create a booking
        if booking_data:
            try:
                logger.info(
                    f"Received booking data for {booking_data.client_name}, creating booking"
                )

                # Convert BookingFunctionArgs to BookingCreate
                booking_create = self._convert_to_booking_create(
                    booking_data, conversation.id
                )

                # Save the booking
                booking = await BookingRepository.create(booking_create)

                # Update conversation state to completed
                await ConversationRepository.update(
                    conversation.id,
                    {"state": ConversationState.COMPLETED, "is_complete": True},
                )

                # Append a confirmation message to the GPT response
                confirmation = "\n\nВаша запись успешно создана. Администратор салона свяжется с вами в ближайшее время для подтверждения. Спасибо за ваше обращение!"
                full_response = response + confirmation

                # Create a bot message for the confirmation
                bot_message = MessageCreate(
                    content=confirmation, 
                    sender_id="bot", 
                    is_from_bot=True,
                    platform=platform
                )
                await MessageRepository.create(conversation.id, bot_message)

                # Mark all previous messages as complete for this platform
                await MessageRepository.mark_platform_messages_as_complete(
                    conversation.id, platform
                )
                
                try:
                    NotificationClient().create_notification({
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
                        "platform": platform.value
                    })
                except Exception as e:
                    logger.error(f"Error creating notification: {e}")

                logger.info(f"Booking created: {booking.id}")

                return UserMessageResponseText(text=full_response), True

            except Exception as e:
                logger.error(f"Error creating booking: {e}", exc_info=True)
                error_message = f"{response}\n\nИзвините, произошла ошибка при сохранении вашей записи. Пожалуйста, попробуйте еще раз позже."

                # Add error message to conversation
                error_bot_message = MessageCreate(
                    content=error_message, 
                    sender_id="bot", 
                    is_from_bot=True,
                    platform=platform
                )
                await MessageRepository.create(conversation.id, error_bot_message)

                return UserMessageResponseText(text=error_message), True

        # If no booking data yet, just return the GPT response as text
        return UserMessageResponseText(text=response), True

    async def _handle_completed(
        self, conversation: Conversation, message_text: str, platform: MessagingPlatform
    ) -> str:
        """
        Handle the completed state of a conversation.

        Args:
            conversation: The conversation
            message_text: The user's message
            platform: The messaging platform

        Returns:
            The response message
        """
        # Check if user wants a new booking
        message_lower = message_text.lower()
        new_booking_phrases = [
            "новая запись",
            "еще запись",
            "другая запись",
            "новая услуга",
            "записаться еще",
            "другая услуга",
        ]

        if any(phrase in message_lower for phrase in new_booking_phrases):
            # Reset conversation for a new booking
            await ConversationRepository.update(
                conversation.id,
                {"state": ConversationState.COLLECTING_INFO, "is_complete": False},
            )

            # Create response
            new_booking_message = "Конечно! Давайте оформим новую запись. Какую услугу вы хотели бы получить в этот раз?"

            # Add bot message to conversation
            bot_message = MessageCreate(
                content=new_booking_message, 
                sender_id="bot", 
                is_from_bot=True,
                platform=platform
            )
            await MessageRepository.create(conversation.id, bot_message)

            return new_booking_message
        else:
            # For any other message, proceed with GPT conversation
            response, _ = await self._handle_conversation_with_gpt(
                conversation, message_text, platform
            )
            if isinstance(response, UserMessageResponseText):
                return response.text
            # Fallback to string representation
            return str(response)

    def _convert_to_booking_create(
        self, booking_args: BookingFunctionArgs, conversation_id: UUID
    ) -> BookingCreate:
        """
        Convert BookingFunctionArgs to BookingCreate.

        Args:
            booking_args: The booking function arguments
            conversation_id: The conversation ID

        Returns:
            A BookingCreate instance
        """
        logger.debug(f"Converting booking data to BookingCreate: {booking_args}")
        # Parse date if provided
        booking_date = None
        if booking_args.booking_date:
            try:
                date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]
                for fmt in date_formats:
                    try:
                        booking_date = datetime.strptime(
                            booking_args.booking_date, fmt
                        ).date()
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.error(f"Error parsing booking date: {e}")

        # Parse time if provided
        booking_time = None
        if booking_args.booking_time:
            try:
                time_formats = ["%H:%M", "%H:%M:%S", "%I:%M %p"]
                for fmt in time_formats:
                    try:
                        booking_time = datetime.strptime(
                            booking_args.booking_time, fmt
                        ).time()
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.error(f"Error parsing booking time: {e}")

        # Convert time_of_day
        time_of_day = None
        if booking_args.time_of_day:
            try:
                time_of_day = TimeOfDay(booking_args.time_of_day)
            except Exception as e:
                logger.error(f"Error parsing time of day: {e}")

        # Convert preferred_contact_time
        preferred_contact_time = None
        if booking_args.preferred_contact_time:
            try:
                preferred_contact_time = TimeOfDay(booking_args.preferred_contact_time)
            except Exception as e:
                logger.error(f"Error parsing preferred contact time: {e}")

        # Create BookingCreate object
        return BookingCreate(
            conversation_id=conversation_id,
            client_name=booking_args.client_name,
            phone=booking_args.phone,
            use_phone_for_whatsapp=booking_args.use_phone_for_whatsapp,
            whatsapp=booking_args.whatsapp,
            preferred_contact_method=ContactMethod(
                booking_args.preferred_contact_method
            ),
            preferred_contact_time=preferred_contact_time,
            service_description=booking_args.service_description,
            booking_date=booking_date,
            booking_time=booking_time,
            time_of_day=time_of_day,
            additional_notes=booking_args.additional_notes,
            status=BookingStatus.PENDING,
        )

    async def send_text_response(self, recipient_id: str, message: str, platform: str = "whatsapp") -> bool:
        """
        Send a text response message to the user via the specified platform.

        Args:
            recipient_id: The user's identifier (phone number for WhatsApp, chat_id for Telegram)
            message: The message to send
            platform: The messaging platform to use

        Returns:
            True if the message was sent successfully, False otherwise
        """
        try:
            from app.services.messaging.factory import MessagingFactory
            from app.services.messaging.interfaces import TextMessageContent
            
            transport = MessagingFactory.get_transport(platform)
            if not transport:
                logger.error(f"Transport not available for platform: {platform}")
                return False
                
            return await transport.send_message(
                recipient_id,
                TextMessageContent(text=message)
            )
        except Exception as e:
            logger.error(f"Error sending {platform} text message: {e}")
            return False

    async def send_response_template(
        self, recipient_id: str, template: str, template_data: Dict[str, Any], platform: str = "whatsapp"
    ) -> bool:
        """
        Send a template response message to the user via the specified platform.

        Args:
            recipient_id: The user's identifier (phone number for WhatsApp, chat_id for Telegram)
            template: The template name
            template_data: The template data
            platform: The messaging platform to use

        Returns:
            True if the message was sent successfully, False otherwise
        """
        try:
            from app.services.messaging.factory import MessagingFactory
            from app.services.messaging.interfaces import TemplateMessageContent
            
            transport = MessagingFactory.get_transport(platform)
            if not transport:
                logger.error(f"Transport not available for platform: {platform}")
                return False
                
            return await transport.send_message(
                recipient_id,
                TemplateMessageContent(template_name=template, template_data=template_data)
            )
        except Exception as e:
            logger.error(f"Error sending {platform} template message: {e}")
            return False