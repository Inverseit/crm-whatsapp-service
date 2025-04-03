import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from uuid import UUID

import asyncio
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.db.repositories.message_repository import MessageRepository
from app.models.booking import BookingFunctionArgs

logger = logging.getLogger(__name__)

class GPTService:
    """Stateless service for interacting with the OpenAI GPT API."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def process_message_with_custom_prompt(
        self, 
        conversation_id: UUID,
        message: str, 
        system_prompt: str,
        message_history: List[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[BookingFunctionArgs]]:
        """
        Process a user message with a custom system prompt.
        
        Args:
            conversation_id: The conversation ID
            message: The user message
            system_prompt: Custom system prompt for this platform/user
            message_history: Optional message history
            
        Returns:
            A tuple of (response_text, booking_data)
        """
        try:
            # Prepare the conversation history
            history = message_history or []
            
            # Add system message if history is empty or doesn't start with system
            if not history or history[0].get("role") != "system":
                history.insert(0, {"role": "system", "content": system_prompt})
            elif history[0].get("role") == "system":
                # Update the system message with the platform-specific one
                history[0]["content"] = system_prompt
            
            # Add current message
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
                except Exception as e:
                    logger.error(f"Error parsing function arguments: {e}", exc_info=True)
            
            return response_content, booking_data
            
        except Exception as e:
            logger.error(f"Error processing message with GPT: {e}", exc_info=True)
            return "Извините, произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз.", None
    
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
                            "enum": ["phone_call", "whatsapp_message", "telegram_message"],
                            "description": "Preferred contact method: phone call, WhatsApp message, or Telegram message"
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