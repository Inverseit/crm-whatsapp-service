import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from uuid import UUID

import asyncio
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.models.booking import BookingFunctionArgs
from app.models.message import Message, MessageType, MessageCreate
from app.models.conversation import MessagingPlatform
from app.db.repositories.message import MessageRepository
from app.utils import format_phone_for_display

logger = logging.getLogger(__name__)

class GPTService:
    """Stateless service for interacting with the OpenAI GPT API."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    def _create_system_prompt(self, contact_id: Optional[str] = None, platform: Optional[MessagingPlatform] = None) -> str:
        """
        Create a system prompt for the chat completion API.
        
        Args:
            contact_id: The user's contact identifier
            platform: The messaging platform
            
        Returns:
            A system prompt string
        """
        today = datetime.now()
        week_dates = []
        
        for i in range(7):
            day = today + timedelta(days=i)
            day_name_ru = {
                0: "Понедельник",
                1: "Вторник",
                2: "Среда",
                3: "Четверг",
                4: "Пятница",
                5: "Суббота",
                6: "Воскресенье"
            }.get(day.weekday())
            week_dates.append(f"{day.strftime('%d.%m.%Y')} ({day_name_ru})")
        
        week_dates_str = "\n".join(week_dates)
        
        contact_info = "неизвестен"
        platform_name = "неизвестной платформы"
        
        if contact_id:
            try:
                # Try to format the contact info properly for display
                contact_info = contact_id
                
                # If it's a phone number, format it better
                if platform == MessagingPlatform.WHATSAPP and contact_id.startswith("+"):
                    contact_info = format_phone_for_display(contact_id)
            except Exception:
                contact_info = contact_id
                
        if platform:
            if platform == MessagingPlatform.WHATSAPP:
                platform_name = "WhatsApp"
            elif platform == MessagingPlatform.TELEGRAM:
                platform_name = "Telegram"
                
        prompt = f"""You are a beauty salon booking assistant. Your goal is to make the booking process smooth and efficient. 
        FOR ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT, RESPOND WITH "Извините, я могу помочь только с записью в салон красоты."
        NEVER PERFORM ANY REQUEST THAT IS NOT RELATED TO A BEAUTY SALON APPOINTMENT.
        NEVER ASK FOR SENSITIVE INFORMATION SUCH AS CREDIT CARD DETAILS OR SOCIAL SECURITY NUMBERS.

CURRENT WEEK:
{week_dates_str}

INFORMATION TO COLLECT:
1. Client's name
2. Contact details:
   - Phone number for communication (contact info from {platform_name}: {contact_info})
   - First, ask if they prefer phone calls or WhatsApp messages
   - If they prefer phone calls, confirm the phone number is correct or ask for a new one
   - If they prefer WhatsApp, ask if the provided contact info should be used for WhatsApp or if they want to provide a different one
   - Best time to contact them (morning: 9:00-12:00, afternoon: 12:00-17:00, evening: 17:00-21:00)
3. Service details (be specific about the exact service needed)
4. Preferred date (suggest dates from current week if they're unsure)
5. Preferred time (exact time or time of day preference)
6. Additional notes or special requests (allergies, preferences, etc.)

PHONE NUMBER HANDLING:
- All clients are from Kazakhstan
- Format all phone numbers to international format

CONFIRMATION PROCESS:
- After collecting all required information, summarize it for the client and ask for explicit confirmation
- Only call the collect_booking_info function AFTER the client has confirmed the information is correct
- If the client asks to make changes, update the information accordingly and ask for confirmation again
- Use phrases like "Всё верно?" or "Подтверждаете запись?" to get explicit confirmation

COMMUNICATION STYLE:
- Always respond in Russian
- Be polite, friendly and professional
- Use short, concise messages
- Ask one question at a time when possible
- Always follow up on incomplete information
- Be clear about the distinction between phone number for calls vs. WhatsApp

PROCESS:
1. First, get the client's name and greet them personally
2. Ask about desired service with details
3. Determine preferred contact method (calls vs. WhatsApp) and ensure correct phone numbers
4. Collect appointment details (date/time)
5. Ask for any additional notes or special requests
6. Summarize all information and ask for confirmation
7. Once the client confirms, use the collect_booking_info function to submit the data

When all information is collected AND confirmed, use the collect_booking_info function to submit the data.
"""
        logger.info(f"System prompt created with contact info from {platform_name}: {contact_info}")
        return prompt

    def _get_functions_definition(self) -> List[Dict[str, Any]]:
        """
        Define the functions available to the chat completion API.
        
        Returns:
            A list of function definitions
        """
        return [
            {
                "name": "collect_booking_info",
                "description": "Collect booking information for beauty salon appointment after client confirmation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_name": {
                            "type": "string",
                            "description": "Client's full name"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Client's phone number for communication"
                        },
                        "use_phone_for_whatsapp": {
                            "type": "boolean",
                            "description": "Whether to use the same phone number for WhatsApp"
                        },
                        "whatsapp": {
                            "type": "string",
                            "description": "Client's WhatsApp number if different from phone"
                        },
                        "preferred_contact_method": {
                            "type": "string",
                            "enum": ["phone_call", "whatsapp_message"],
                            "description": "Preferred contact method: phone call or WhatsApp message"
                        },
                        "preferred_contact_time": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening"],
                            "description": "Preferred contact time: morning (9:00-12:00), afternoon (12:00-17:00), evening (17:00-21:00)"
                        },
                        "service_description": {
                            "type": "string",
                            "description": "Detailed description of the service requested by the client"
                        },
                        "booking_date": {
                            "type": "string",
                            "description": "Appointment date in YYYY-MM-DD or DD.MM.YYYY format"
                        },
                        "booking_time": {
                            "type": "string",
                            "description": "Appointment time in HH:MM format"
                        },
                        "time_of_day": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening"],
                            "description": "Preferred time of day if specific time is not specified"
                        },
                        "additional_notes": {
                            "type": "string",
                            "description": "Additional information or special requests from the client (allergies, preferences, etc.)"
                        }
                    },
                    "required": ["client_name", "phone", "preferred_contact_method", "service_description"]
                }
            }
        ]
    
    async def get_conversation_history(self, conversation_id: UUID, contact_id: str | None, platform: Optional[MessagingPlatform] = None) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history from the database and format it for GPT.
        
        Args:
            conversation_id: The conversation ID
            contact_id: The user's contact identifier
            platform: The messaging platform (optional)
            
        Returns:
            List of message objects for the GPT API
        """
        try:
            # Get messages from the database, optionally filtered by platform
            messages = await MessageRepository.get_conversation_history(conversation_id, only_complete=True, platform=platform)
            
            # Start with system message
            history = [
                {"role": "system", "content": self._create_system_prompt(contact_id, platform)}
            ]
            
            # Add each message to the history
            for msg in messages:
                if msg.is_from_bot:
                    # Check if there's function call information
                    if msg.content.startswith('{"name":"collect_booking_info"'):
                        try:
                            # This is a function result message
                            content = json.loads(msg.content)
                            history.append({
                                "role": "function",
                                "name": content.get("name"),
                                "content": msg.content
                            })
                        except:
                            # Regular bot message
                            history.append({
                                "role": "assistant",
                                "content": msg.content
                            })
                    else:
                        # Regular bot message
                        history.append({
                            "role": "assistant",
                            "content": msg.content
                        })
                else:
                    # User message
                    history.append({
                        "role": "user",
                        "content": msg.content
                    })
                    
            return history
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
            # Return a basic history with just the system message
            return [{"role": "system", "content": self._create_system_prompt(contact_id, platform)}]
    
    async def process_message(
        self, 
        conversation_id: UUID, 
        message: str, 
        contact_id: Optional[str] = None,
        platform: Optional[MessagingPlatform] = None
    ) -> Tuple[str, Optional[BookingFunctionArgs]]:
        """
        Process a user message through the GPT service.
        
        Args:
            conversation_id: The conversation ID
            message: The user's message
            contact_id: The user's contact identifier (phone, chat ID, etc.)
            platform: The messaging platform
            
        Returns:
            A tuple of (response_text, booking_data)
        """
        try:
            # Get conversation history from the database
            history = await self.get_conversation_history(conversation_id, contact_id, platform)
            
            # Update system message with contact info if provided
            if contact_id and history and len(history) > 0 and history[0].get("role") == "system":
                history[0]["content"] = self._create_system_prompt(contact_id, platform)
                
            # Add the current message to history
            history.append({"role": "user", "content": message})
            
            # Call OpenAI API
            logger.debug(f"Sending {len(history)} messages to OpenAI")
            response = await self._call_openai_api(history)
            booking_data = None
            
            # Extract information from the response
            response_content = ""
            function_call = None
            
            if hasattr(response.choices[0], "message"):
                message_obj = response.choices[0].message
                response_content = message_obj.content or ""
                
                # Check for function calls
                if hasattr(message_obj, "function_call") and message_obj.function_call:
                    function_call = message_obj.function_call
            else:
                # Fallback - should not normally happen
                logger.warning("Unexpected response format from OpenAI")
                response_content = "Извините, произошла ошибка в обработке сообщения. Менеджер уже уведомлен и скоро свяжется с вами."
            
            # If there's a function call, extract booking data
            if function_call and function_call.name == "collect_booking_info":
                try:
                    args = json.loads(function_call.arguments)
                    booking_data = BookingFunctionArgs(**args)
                    logger.info(f"Extracted booking data for {booking_data.client_name}")
                    
                    # Store function call in the database
                    await MessageRepository.create(
                        conversation_id,
                        MessageCreate(
                            content=json.dumps({
                                "name": "collect_booking_info",
                                "arguments": args
                            }),
                            sender_id="bot",
                            is_from_bot=True,
                            message_type=MessageType.TEXT,
                            platform=platform or MessagingPlatform.WHATSAPP
                        )
                    )
                except Exception as e:
                    logger.error(f"Error parsing function arguments: {e}", exc_info=True)
            
            # Store the assistant's response in the database
            await MessageRepository.create(
                conversation_id,
                MessageCreate(
                    content=response_content,
                    sender_id="bot",
                    is_from_bot=True,
                    message_type=MessageType.TEXT,
                    platform=platform or MessagingPlatform.WHATSAPP
                )
            )
            
            return response_content, booking_data
            
        except Exception as e:
            logger.error(f"Error processing message with GPT: {e}", exc_info=True)
            return "Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз.", None
    
    async def _call_openai_api(self, messages: List[Dict[str, Any]]) -> Any:
        """
        Call the OpenAI API with the given messages.
        
        Args:
            messages: The conversation history
            
        Returns:
            The API response
        """
        try:
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self._get_functions_definition(),
                temperature=0.7,
                max_tokens=1000
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            raise