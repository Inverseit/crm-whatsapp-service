from enum import Enum
from datetime import datetime, date, time
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import phonenumbers
from app.db.models import TimeOfDay, ContactMethod, BookingStatus

class PhoneNumber(BaseModel):
    """Model for validating and normalizing phone numbers."""
    number: str
    
    @field_validator('number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize a phone number to E.164 format."""
        try:
            # Parse phone number with phonenumbers library
            v = v.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            
            # Parse and validate the phone number
            phone_number = phonenumbers.parse(v)
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError('Invalid phone number format')
            
            # Format to E164 format for consistency
            return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
        except Exception as e:
            # Log the error but still return the original number
            print(f'Error formatting phone number: {e}')
            return v

class ContactInfo(BaseModel):
    """Contact information for a client."""
    phone: str = Field(..., description="Client's phone number in E.164 format")
    use_phone_for_whatsapp: bool = Field(True, description="Whether to use the same phone number for WhatsApp")
    whatsapp: Optional[str] = Field(None, description="Client's WhatsApp number if different from phone")
    preferred_contact_method: ContactMethod = Field(..., description="Client's preferred contact method")
    preferred_contact_time: Optional[TimeOfDay] = Field(None, description="Client's preferred time to be contacted")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize the phone number."""
        return PhoneNumber(number=v).number
    
    @model_validator(mode='after')
    def set_whatsapp_number(self) -> 'ContactInfo':
        """Set WhatsApp number to phone number if use_phone_for_whatsapp is True."""
        if self.use_phone_for_whatsapp and not self.whatsapp:
            self.whatsapp = self.phone
        elif self.whatsapp:
            self.whatsapp = PhoneNumber(number=self.whatsapp).number
        return self

class BookingBase(BaseModel):
    """Base model for booking information."""
    client_name: str = Field(..., description="Client's full name")
    phone: str = Field(..., description="Client's phone number in E.164 format")
    use_phone_for_whatsapp: bool = Field(True, description="Whether to use the same phone number for WhatsApp")
    whatsapp: Optional[str] = Field(None, description="Client's WhatsApp number if different from phone")
    preferred_contact_method: ContactMethod = Field(..., description="Preferred contact method (phone call or WhatsApp)")
    preferred_contact_time: Optional[TimeOfDay] = Field(None, description="Preferred time of day to be contacted")
    service_description: str = Field(..., description="Detailed description of the service requested")
    booking_date: Optional[date] = Field(None, description="Appointment date")
    booking_time: Optional[time] = Field(None, description="Appointment time")
    time_of_day: Optional[TimeOfDay] = Field(None, description="Preferred time of day if specific time not provided")
    additional_notes: Optional[str] = Field(None, description="Additional information or special requests")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize the phone number."""
        return PhoneNumber(number=v).number
    
    @model_validator(mode='after')
    def set_whatsapp_number(self) -> 'BookingBase':
        """Set WhatsApp number to phone number if use_phone_for_whatsapp is True."""
        if self.use_phone_for_whatsapp and not self.whatsapp:
            self.whatsapp = self.phone
        elif self.whatsapp:
            self.whatsapp = PhoneNumber(number=self.whatsapp).number
        return self

class BookingCreate(BookingBase):
    """Model for creating a new booking."""
    conversation_id: UUID = Field(..., description="ID of the conversation this booking belongs to")
    status: BookingStatus = Field(default=BookingStatus.PENDING, description="Current status of the booking")

class BookingResponse(BookingBase):
    """Complete booking model with all fields for API responses."""
    id: UUID = Field(..., description="Unique booking identifier")
    conversation_id: UUID = Field(..., description="ID of the conversation this booking belongs to")
    status: BookingStatus = Field(..., description="Current status of the booking")
    created_at: datetime = Field(..., description="When the booking was created")
    updated_at: datetime = Field(..., description="When the booking was last updated")
    
    model_config = ConfigDict(from_attributes=True)

class BookingUpdate(BaseModel):
    """Model for updating an existing booking. All fields are optional."""
    client_name: Optional[str] = Field(None, description="Client's full name")
    phone: Optional[str] = Field(None, description="Client's phone number")
    use_phone_for_whatsapp: Optional[bool] = Field(None, description="Whether to use the same phone number for WhatsApp")
    whatsapp: Optional[str] = Field(None, description="Client's WhatsApp number if different from phone")
    preferred_contact_method: Optional[ContactMethod] = Field(None, description="Preferred contact method")
    preferred_contact_time: Optional[TimeOfDay] = Field(None, description="Preferred time to be contacted")
    service_description: Optional[str] = Field(None, description="Service description")
    booking_date: Optional[date] = Field(None, description="Appointment date")
    booking_time: Optional[time] = Field(None, description="Appointment time")
    time_of_day: Optional[TimeOfDay] = Field(None, description="Preferred time of day")
    additional_notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[BookingStatus] = Field(None, description="Booking status")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize the phone number."""
        if v is not None:
            return PhoneNumber(number=v).number
        return None
    
    @field_validator('whatsapp')
    @classmethod
    def validate_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize the WhatsApp number."""
        if v is not None:
            return PhoneNumber(number=v).number
        return None

class BookingFunctionArgs(BaseModel):
    """Model for function arguments when handling booking data from GPT."""
    client_name: str = Field(..., description="Client's full name")
    phone: str = Field(..., description="Client's phone number")
    use_phone_for_whatsapp: bool = Field(True, description="Whether to use phone number for WhatsApp")
    whatsapp: Optional[str] = Field(None, description="Client's WhatsApp number if different")
    preferred_contact_method: str = Field(..., description="Preferred contact method (phone_call, whatsapp_message, or telegram_message)")
    preferred_contact_time: Optional[str] = Field(None, description="Preferred contact time (morning, afternoon, evening)")
    service_description: str = Field(..., description="Service description")
    booking_date: Optional[str] = Field(None, description="Appointment date as string")
    booking_time: Optional[str] = Field(None, description="Appointment time as string")
    time_of_day: Optional[str] = Field(None, description="Preferred time of day if specific time not provided")
    additional_notes: Optional[str] = Field(None, description="Additional notes")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_name": "Anna Petrova",
                "phone": "+77771234567",
                "use_phone_for_whatsapp": True,
                "preferred_contact_method": "whatsapp_message",
                "preferred_contact_time": "evening",
                "service_description": "Маникюр и педикюр",
                "booking_date": "2025-03-15",
                "time_of_day": "afternoon",
                "additional_notes": "Аллергия на лак определенной марки"
            }
        }
    )