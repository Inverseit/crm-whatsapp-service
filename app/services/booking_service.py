import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID
from datetime import datetime, date, time

from app.db.repositories.booking import BookingRepository
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.message import MessageRepository
from app.models.booking import Booking, BookingCreate, BookingStatus, TimeOfDay, ContactMethod, BookingFunctionArgs
from app.models.conversation import Conversation, ConversationState
from app.models.message import Message, MessageCreate, MessageType
from app.services.gpt_service import GPTService

logger = logging.getLogger(__name__)

class BookingManager:
    """Manager for booking-related operations."""
    
    def __init__(self, gpt_service: GPTService):
        self.gpt_service = gpt_service
    
    async def process_user_message(self, phone: str, message_text: str) -> str:
        """
        Process a user message and update the conversation state accordingly.
        
        Args:
            phone: The user's phone number
            message_text: The message content
            
        Returns:
            The response message
        """
        # Get or create conversation
        conversation = await ConversationRepository.get_or_create(phone)
        
        # Create a message record
        user_message = MessageCreate(
            content=message_text,
            sender_id=phone,
            is_from_bot=False
        )
        await MessageRepository.create(conversation.id, user_message)
        
        # Process message based on conversation state
        if conversation.state == ConversationState.GREETING:
            return await self._handle_greeting(conversation)
        elif conversation.state == ConversationState.COLLECTING_INFO:
            return await self._handle_collecting_info(conversation, message_text)
        elif conversation.state == ConversationState.CONFIRMING:
            return await self._handle_confirming(conversation, message_text)
        elif conversation.state == ConversationState.COMPLETED:
            return await self._handle_completed(conversation, message_text)
        else:
            return await self._handle_collecting_info(conversation, message_text)
    
    async def _handle_greeting(self, conversation: Conversation) -> str:
        """
        Handle the greeting state of a conversation.
        
        Args:
            conversation: The conversation
            
        Returns:
            The response message
        """
        # Update conversation state
        await ConversationRepository.update(
            conversation.id, 
            {"state": ConversationState.COLLECTING_INFO}
        )
        
        # Send greeting message
        greeting = "Здравствуйте! Я бот салона красоты. Я помогу вам записаться на процедуру. Подскажите, пожалуйста, как к вам обращаться?"
        
        # Create a bot message
        bot_message = MessageCreate(
            content=greeting,
            sender_id="bot",
            is_from_bot=True
        )
        await MessageRepository.create(conversation.id, bot_message)
        
        return greeting
    
    async def _handle_collecting_info(self, conversation: Conversation, message_text: str) -> str:
        """
        Handle the collecting info state of a conversation.
        
        Args:
            conversation: The conversation
            message_text: The user's message
            
        Returns:
            The response message
        """
        # Process message with GPT
        response, booking_data = await self.gpt_service.process_message(
            str(conversation.id),
            message_text,
            conversation.phone_number
        )
        
        # If booking data was collected, move to confirming state
        if booking_data:
            try:
                # Create confirmation message
                confirmation_message = await self._create_confirmation_message(conversation.id, booking_data)
                
                # Update conversation state
                await ConversationRepository.update(
                    conversation.id, 
                    {"state": ConversationState.CONFIRMING}
                )
                
                # Save the confirmation message
                bot_message = MessageCreate(
                    content=confirmation_message,
                    sender_id="bot",
                    is_from_bot=True
                )
                await MessageRepository.create(conversation.id, bot_message)
                
                return confirmation_message
                
            except Exception as e:
                logger.error(f"Error creating booking confirmation: {e}")
                error_message = "Извините, произошла ошибка при обработке данных бронирования. Пожалуйста, попробуйте еще раз."
                
                # Save error message
                bot_message = MessageCreate(
                    content=error_message,
                    sender_id="bot",
                    is_from_bot=True
                )
                await MessageRepository.create(conversation.id, bot_message)
                
                return error_message
        
        # If no booking data was collected yet, just return the GPT response
        bot_message = MessageCreate(
            content=response,
            sender_id="bot",
            is_from_bot=True
        )
        await MessageRepository.create(conversation.id, bot_message)
        
        return response
    
    async def _handle_confirming(self, conversation: Conversation, message_text: str) -> str:
        """
        Handle the confirming state of a conversation.
        
        Args:
            conversation: The conversation
            message_text: The user's message
            
        Returns:
            The response message
        """
        # Simple confirmation logic - look for confirmation words in Russian
        message_lower = message_text.lower()
        confirmation_words = ["да", "конечно", "верно", "правильно", "согласен", "подтверждаю", "ок", "хорошо"]
        rejection_words = ["нет", "неверно", "неправильно", "не так", "ошибка", "изменить", "нужно исправить"]
        
        is_confirmed = any(word in message_lower for word in confirmation_words)
        is_rejected = any(word in message_lower for word in rejection_words)
        
        if is_confirmed and not is_rejected:
            # Get all messages from the conversation history
            messages = await MessageRepository.get_conversation_history(conversation.id)
            
            # Extract booking data from the conversation
            booking_data = await self._extract_booking_data_from_conversation(conversation.id, messages)
            
            if booking_data:
                try:
                    # Convert BookingFunctionArgs to BookingCreate
                    booking_create = self._convert_to_booking_create(booking_data, conversation.id)
                    
                    # Save the booking
                    booking = await BookingRepository.create(booking_create)
                    
                    # Update conversation state
                    await ConversationRepository.update(
                        conversation.id, 
                        {"state": ConversationState.COMPLETED, "is_complete": True}
                    )
                    
                    # Create completion message
                    completion_message = "Спасибо за подтверждение! Ваша заявка на запись принята. " \
                                       "Администратор салона свяжется с вами в ближайшее время для окончательного подтверждения записи. " \
                                       "Хорошего дня!"
                    
                    # Add bot message to conversation
                    bot_message = MessageCreate(
                        content=completion_message,
                        sender_id="bot",
                        is_from_bot=True
                    )
                    await MessageRepository.create(conversation.id, bot_message)
                    
                    logger.info(f"Booking confirmed: {booking.id}")
                    
                    return completion_message
                except Exception as e:
                    logger.error(f"Error creating booking: {e}")
                    error_message = "Извините, произошла ошибка при сохранении вашей записи. Пожалуйста, попробуйте еще раз."
                    
                    # Add bot message to conversation
                    bot_message = MessageCreate(
                        content=error_message,
                        sender_id="bot",
                        is_from_bot=True
                    )
                    await MessageRepository.create(conversation.id, bot_message)
                    
                    return error_message
            else:
                # This shouldn't happen, but just in case
                error_message = "Извините, произошла ошибка с вашей заявкой. Пожалуйста, начните процесс записи заново."
                
                # Reset conversation state
                await ConversationRepository.update(
                    conversation.id, 
                    {"state": ConversationState.GREETING}
                )
                
                # Add bot message to conversation
                bot_message = MessageCreate(
                    content=error_message,
                    sender_id="bot",
                    is_from_bot=True
                )
                await MessageRepository.create(conversation.id, bot_message)
                
                return error_message
                
        elif is_rejected:
            # User didn't confirm, go back to collecting info
            await ConversationRepository.update(
                conversation.id, 
                {"state": ConversationState.COLLECTING_INFO}
            )
            
            # Reset the GPT conversation for a new booking attempt
            self.gpt_service.reset_conversation_for_new_booking(
                str(conversation.id), 
                conversation.phone_number
            )
            
            # Create correction response
            correction_message = "Понял, давайте исправим информацию. Пожалуйста, уточните, что именно нужно изменить?"
            
            # Add bot message to conversation
            bot_message = MessageCreate(
                content=correction_message,
                sender_id="bot",
                is_from_bot=True
            )
            await MessageRepository.create(conversation.id, bot_message)
            
            return correction_message
        else:
            # Unclear response, ask for explicit confirmation
            clarification_message = "Извините, я не совсем понял ваш ответ. Пожалуйста, подтвердите, верна ли информация о записи? Ответьте 'Да' или 'Нет'."
            
            # Add bot message to conversation
            bot_message = MessageCreate(
                content=clarification_message,
                sender_id="bot",
                is_from_bot=True
            )
            await MessageRepository.create(conversation.id, bot_message)
            
            return clarification_message
    
    async def _handle_completed(self, conversation: Conversation, message_text: str) -> str:
        """
        Handle the completed state of a conversation.
        
        Args:
            conversation: The conversation
            message_text: The user's message
            
        Returns:
            The response message
        """
        # Check if user wants a new booking
        message_lower = message_text.lower()
        new_booking_phrases = ["новая запись", "еще запись", "другая запись", "новая услуга", "записаться еще", "другая услуга"]
        
        if any(phrase in message_lower for phrase in new_booking_phrases):
            # Reset conversation for a new booking
            await ConversationRepository.update(
                conversation.id, 
                {"state": ConversationState.COLLECTING_INFO, "is_complete": False}
            )
            
            # Reset GPT conversation
            self.gpt_service.reset_conversation_for_new_booking(
                str(conversation.id), 
                conversation.phone_number
            )
            
            # Create response
            new_booking_message = "Конечно! Давайте оформим новую запись. Какую услугу вы хотели бы получить в этот раз?"
            
            # Add bot message to conversation
            bot_message = MessageCreate(
                content=new_booking_message,
                sender_id="bot",
                is_from_bot=True
            )
            await MessageRepository.create(conversation.id, bot_message)
            
            return new_booking_message
        else:
            thank_you_message = "Спасибо за ваше сообщение! Ваша запись уже подтверждена. Если у вас есть дополнительные вопросы или вы хотите сделать новую запись, просто напишите об этом."
            
            # Add bot message to conversation
            bot_message = MessageCreate(
                content=thank_you_message,
                sender_id="bot",
                is_from_bot=True
            )
            await MessageRepository.create(conversation.id, bot_message)
            
            return thank_you_message
    
    async def _create_confirmation_message(self, conversation_id: UUID, booking: BookingFunctionArgs) -> str:
        """
        Create a formatted confirmation message with booking details.
        
        Args:
            conversation_id: The conversation ID
            booking: The booking data
            
        Returns:
            A formatted confirmation message
        """
        # Format date
        date_str = booking.booking_date or "Не указана"
        
        # Format time
        if booking.booking_time:
            time_str = booking.booking_time
        elif booking.time_of_day:
            time_map = {
                "morning": "Утро (9:00-12:00)",
                "afternoon": "День (12:00-17:00)",
                "evening": "Вечер (17:00-21:00)"
            }
            time_str = time_map.get(booking.time_of_day, "Не указано")
        else:
            time_str = "Не указано"
        
        # Format contact method
        contact_method_str = "Не указан"
        if booking.preferred_contact_method:
            if booking.preferred_contact_method == "phone_call":
                contact_method_str = "Звонок по телефону"
            elif booking.preferred_contact_method == "whatsapp_message":
                contact_method_str = "Сообщение в WhatsApp"
        
        # Format contact time
        contact_time_str = "Не указано"
        if booking.preferred_contact_time:
            time_map = {
                "morning": "Утро (9:00-12:00)",
                "afternoon": "День (12:00-17:00)",
                "evening": "Вечер (17:00-21:00)"
            }
            contact_time_str = time_map.get(booking.preferred_contact_time, "Не указано")
        
        # Format phone numbers for display
        phone_display = booking.phone
        
        # Format WhatsApp number (if different)
        whatsapp_display = "Тот же, что и телефон для связи"
        if not booking.use_phone_for_whatsapp and booking.whatsapp:
            whatsapp_display = booking.whatsapp
        
        # Store booking data in GPT service for later retrieval
        conversation_id_str = str(conversation_id)
        self.gpt_service.add_message_to_history(
            conversation_id_str,
            "function",
            json.dumps({
                "name": "collect_booking_info",
                "arguments": booking.model_dump()
            })
        )
        
        # Build the confirmation message
        return f"Спасибо за предоставленную информацию! Пожалуйста, проверьте детали вашей записи:\n\n" \
               f"Имя: {booking.client_name}\n" \
               f"Телефон: {phone_display}\n" \
               f"WhatsApp: {whatsapp_display}\n" \
               f"Предпочтительный способ связи: {contact_method_str}\n" \
               f"Предпочтительное время для связи: {contact_time_str}\n" \
               f"Услуга: {booking.service_description}\n" \
               f"Дата: {date_str}\n" \
               f"Время: {time_str}\n" \
               f"Дополнительная информация: {booking.additional_notes or 'Не указана'}\n\n" \
               f"Всё верно? Ответьте 'Да' для подтверждения или 'Нет' для внесения изменений."
               
    async def _extract_booking_data_from_conversation(self, conversation_id: UUID, messages: List[Message]) -> Optional[BookingFunctionArgs]:
        """
        Extract booking data from the conversation history.
        
        Args:
            conversation_id: The conversation ID
            messages: The messages in the conversation
            
        Returns:
            The booking data, if found
        """
        # Get the conversation history from the GPT service
        conversation_id_str = str(conversation_id)
        history = self.gpt_service.get_conversation_history(conversation_id_str)
        
        # Look for function calls with booking data
        for msg in reversed(history):
            if msg.get("role") == "function" and "collect_booking_info" in msg.get("content", ""):
                try:
                    # Parse the function call
                    content = json.loads(msg.get("content", "{}"))
                    if "arguments" in content:
                        return BookingFunctionArgs(**content["arguments"])
                except Exception as e:
                    logger.error(f"Error parsing booking data from conversation: {e}")
                    
        # If not found in GPT history, check for assistant messages with function calls
        for msg in reversed(history):
            if msg.get("role") == "assistant" and msg.get("function_call", {}).get("name") == "collect_booking_info":
                try:
                    # Parse the function call arguments
                    args = json.loads(msg["function_call"]["arguments"])
                    return BookingFunctionArgs(**args)
                except Exception as e:
                    logger.error(f"Error parsing booking data from function call: {e}")
        
        return None
    
    def _convert_to_booking_create(self, booking_args: BookingFunctionArgs, conversation_id: UUID) -> BookingCreate:
        """
        Convert BookingFunctionArgs to BookingCreate.
        
        Args:
            booking_args: The booking function arguments
            conversation_id: The conversation ID
            
        Returns:
            A BookingCreate instance
        """
        # Parse date if provided
        booking_date = None
        if booking_args.booking_date:
            try:
                date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]
                for fmt in date_formats:
                    try:
                        booking_date = datetime.strptime(booking_args.booking_date, fmt).date()
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
                        booking_time = datetime.strptime(booking_args.booking_time, fmt).time()
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
            preferred_contact_method=ContactMethod(booking_args.preferred_contact_method),
            preferred_contact_time=preferred_contact_time,
            service_description=booking_args.service_description,
            booking_date=booking_date,
            booking_time=booking_time,
            time_of_day=time_of_day,
            additional_notes=booking_args.additional_notes,
            status=BookingStatus.PENDING
        )