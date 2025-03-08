import json
import logging
from typing import Dict, List, Optional, Tuple, Any, cast
from datetime import datetime, timedelta
from uuid import UUID

import asyncio
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from app.config import settings
from app.models.booking import BookingFunctionArgs, TimeOfDay, ContactMethod
from app.utils import format_phone_for_display

logger = logging.getLogger(__name__)

class GPTService:
    """Service for interacting with the OpenAI GPT API."""
    
    def __init__(self, api_key: str = settings.openai_api_key, model: str = settings.openai_model):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.conversation_histories: Dict[str, List[ChatCompletionMessageParam]] = {}
    
    def _create_system_prompt(self, phone_number: Optional[str] = None) -> str:
        """
        Create a system prompt for the chat completion API.
        
        Args:
            phone_number: The user's phone number, if known
            
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
        
        formatted_phone = "неизвестен"
        if phone_number:
            try:
                # Try to format the phone number properly for display
                formatted_phone = format_phone_for_display(phone_number)
            except Exception:
                formatted_phone = phone_number
        
        prompt = f"""You are a beauty salon booking assistant. Your goal is to make the booking process smooth and efficient.

CURRENT WEEK:
{week_dates_str}

INFORMATION TO COLLECT:
1. Client's name
2. Contact details:
   - Phone number for communication (already known: {formatted_phone})
   - First, ask if they prefer phone calls or WhatsApp messages
   - If they prefer phone calls, confirm the phone number is correct or ask for a new one
   - If they prefer WhatsApp, ask if the provided phone number should be used for WhatsApp or if they want to provide a different one
   - Best time to contact them (morning: 9:00-12:00, afternoon: 12:00-17:00, evening: 17:00-21:00)
3. Service details (be specific about the exact service needed)
4. Preferred date (suggest dates from current week if they're unsure)
5. Preferred time (exact time or time of day preference)
6. Additional notes or special requests (allergies, preferences, etc.)

PHONE NUMBER HANDLING:
- All clients are from Kazakhstan
- Kazakhstan phone numbers typically start with +7
- If the user provides a number starting with 8, replace it with +7
- If they don't include a country code, assume +7 (Kazakhstan)
- Format all phone numbers to international format

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
6. Double-check all information and use the function to collect the booking data

When all information is collected, use the collect_booking_info function to submit the data.
"""
        logger.info(f"System prompt created with phone: {formatted_phone}")
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
                "description": "Collect booking information for beauty salon appointment",
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
    
    def _initialize_conversation(self, conversation_id: str, phone_number: Optional[str] = None) -> None:
        """
        Initialize a conversation history or reset it with a new system prompt.
        
        Args:
            conversation_id: The conversation ID
            phone_number: The user's phone number, if known
        """
        if conversation_id not in self.conversation_histories:
            self.conversation_histories[conversation_id] = [
                {"role": "system", "content": self._create_system_prompt(phone_number)}
            ]
    
    async def process_message(self, conversation_id: str, message: str, phone_number: Optional[str] = None) -> Tuple[str, Optional[BookingFunctionArgs]]:
        """
        Process a user message through the GPT service.
        
        Args:
            conversation_id: The conversation ID
            message: The user's message
            phone_number: The user's phone number, if known
            
        Returns:
            A tuple of (response_text, booking_data)
        """
        self._initialize_conversation(conversation_id, phone_number)
        self.conversation_histories[conversation_id].append({"role": "user", "content": message})
        
        try:
            response = await self._call_openai_api(self.conversation_histories[conversation_id])
            booking_data = None
            message_object = response.choices[0].message
            response_content = message_object.content or ""
            
            if message_object.function_call and message_object.function_call.name == "collect_booking_info":
                try:
                    args = json.loads(message_object.function_call.arguments)
                    booking_data = BookingFunctionArgs(**args)
                    logger.info(f"Extracted booking data: {booking_data}")
                except Exception as e:
                    logger.error(f"Error parsing function arguments: {e}")
            
            if message_object.function_call:
                self.conversation_histories[conversation_id].append({
                    "role": "assistant",
                    "content": response_content,
                    "function_call": {
                        "name": message_object.function_call.name,
                        "arguments": message_object.function_call.arguments
                    }
                })
            else:
                self.conversation_histories[conversation_id].append({
                    "role": "assistant",
                    "content": response_content
                })
            
            return response_content, booking_data
            
        except Exception as e:
            logger.error(f"Error processing message with GPT: {e}")
            return "Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз.", None
    
    def reset_conversation_for_new_booking(self, conversation_id: str, phone_number: Optional[str] = None) -> None:
        """
        Reset conversation history for a new booking while keeping system prompt.
        
        Args:
            conversation_id: The conversation ID
            phone_number: The user's phone number, if known
        """
        if conversation_id in self.conversation_histories:
            updated_system_prompt = self._create_system_prompt(phone_number)
            updated_system_message = {"role": "system", "content": updated_system_prompt}
            self.conversation_histories[conversation_id] = [updated_system_message]
    
    async def _call_openai_api(self, messages: List[Dict[str, Any]]) -> Any:
        """
        Call the OpenAI API with the given messages.
        
        Args:
            messages: The conversation history
            
        Returns:
            The API response
        """
        return await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=self._get_functions_definition(),
            temperature=0.7,
            max_tokens=1000
        )
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a given conversation ID.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            The conversation history
        """
        return self.conversation_histories.get(conversation_id, [])
    
    def add_message_to_history(self, conversation_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            conversation_id: The conversation ID
            role: The message role (user or assistant)
            content: The message content
        """
        self._initialize_conversation(conversation_id)
        self.conversation_histories[conversation_id].append({
            "role": role,
            "content": content
        })