# app/models/booking.py
from enum import Enum
from datetime import datetime, date, time
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import phonenumbers

class TimeOfDay(str, Enum):
    MORNING = "morning"  # 9:00 to 12:00
    AFTERNOON = "afternoon"  # 12:00 to 17:00
    EVENING = "evening"  # 17:00 to 21:00
    
    @classmethod
    def from_time(cls, t: time) -> Optional["TimeOfDay"]:
        if time(9, 0) <= t < time(12, 0):
            return cls.MORNING
        elif time(12, 0) <= t < time(17, 0):
            return cls.AFTERNOON
        elif time(17, 0) <= t < time(21, 0):
            return cls.EVENING
        else:
            return None

class ContactMethod(str, Enum):
    PHONE_CALL = "phone_call"
    WHATSAPP_MESSAGE = "whatsapp_message"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class PhoneNumber(BaseModel):
    number: str
    
    @field_validator('number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        try:
            # Parse phone number with phonenumbers library
            v = v.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            
            # If no country code is provided, assume Kazakhstan (+7)
            if not v.startswith('+'):
                if v.startswith('8'):
                    v = '+7' + v[1:]
                else:
                    v = '+7' + v
            
            # Parse and validate the phone number
            phone_number = phonenumbers.parse(v)
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError('Invalid phone number format')
            
            # Format to E164 format for consistency
            return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
        except Exception as e:
            raise ValueError(f'Invalid phone number format: {e}')

class ContactInfo(BaseModel):
    phone: str
    use_phone_for_whatsapp: bool = True
    whatsapp: Optional[str] = None
    preferred_contact_method: ContactMethod
    preferred_contact_time: Optional[TimeOfDay] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return PhoneNumber(number=v).number
    
    @field_validator('whatsapp')
    @classmethod
    def validate_whatsapp(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if v is None and values.get('use_phone_for_whatsapp', True):
            return values.get('phone')
        elif v is not None:
            return PhoneNumber(number=v).number
        return None

class BookingBase(BaseModel):
    client_name: str
    phone: str
    use_phone_for_whatsapp: bool = True
    whatsapp: Optional[str] = None
    preferred_contact_method: ContactMethod
    preferred_contact_time: Optional[TimeOfDay] = None
    service_description: str
    booking_date: Optional[date] = None
    booking_time: Optional[time] = None
    time_of_day: Optional[TimeOfDay] = None
    additional_notes: Optional[str] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return PhoneNumber(number=v).number
    
    @field_validator('whatsapp')
    @classmethod
    def validate_whatsapp(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if v is None and values.get('use_phone_for_whatsapp', True):
            return values.get('phone')
        elif v is not None:
            return PhoneNumber(number=v).number
        return None

class BookingCreate(BookingBase):
    conversation_id: UUID
    status: BookingStatus = BookingStatus.PENDING

class Booking(BookingBase):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    status: BookingStatus = BookingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert booking to a dictionary that can be serialized to JSON."""
        result = self.model_dump(exclude_none=True)
        
        # Convert date and time to strings
        if result.get('booking_date'):
            result['booking_date'] = result['booking_date'].isoformat()
        if result.get('booking_time'):
            result['booking_time'] = result['booking_time'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('last_updated'):
            result['last_updated'] = result['last_updated'].isoformat()
            
        return result

class BookingUpdate(BaseModel):
    """Booking update model with all fields optional."""
    client_name: Optional[str] = None
    phone: Optional[str] = None
    use_phone_for_whatsapp: Optional[bool] = None
    whatsapp: Optional[str] = None
    preferred_contact_method: Optional[ContactMethod] = None
    preferred_contact_time: Optional[TimeOfDay] = None
    service_description: Optional[str] = None
    booking_date: Optional[date] = None
    booking_time: Optional[time] = None
    time_of_day: Optional[TimeOfDay] = None
    additional_notes: Optional[str] = None
    status: Optional[BookingStatus] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return PhoneNumber(number=v).number
        return None
    
    @field_validator('whatsapp')
    @classmethod
    def validate_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return PhoneNumber(number=v).number
        return None

class BookingFunctionArgs(BaseModel):
    client_name: str
    phone: str
    use_phone_for_whatsapp: bool = True
    whatsapp: Optional[str] = None
    preferred_contact_method: str
    preferred_contact_time: Optional[str] = None
    service_description: str
    booking_date: Optional[str] = None
    booking_time: Optional[str] = None
    time_of_day: Optional[str] = None
    additional_notes: Optional[str] = None