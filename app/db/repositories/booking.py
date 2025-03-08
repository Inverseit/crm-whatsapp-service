from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import date, time

from app.db.connection import db
from app.models.booking import Booking, BookingCreate, BookingUpdate, BookingStatus, TimeOfDay, ContactMethod

class BookingRepository:
    """Repository for booking data access operations."""
    
    @staticmethod
    async def create(booking: BookingCreate) -> Booking:
        """Create a new booking in the database."""
        query = """
        INSERT INTO booking (
            id, conversation_id, client_name, phone, use_phone_for_whatsapp, 
            whatsapp, preferred_contact_method, preferred_contact_time, 
            service_description, booking_date, booking_time, time_of_day, 
            additional_notes, status
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
        ) RETURNING *
        """
        
        booking_id = UUID(str(booking.id)) if hasattr(booking, 'id') else uuid4()
        
        values = (
            booking_id,
            booking.conversation_id,
            booking.client_name,
            booking.phone,
            booking.use_phone_for_whatsapp,
            booking.whatsapp,
            booking.preferred_contact_method.value,
            booking.preferred_contact_time.value if booking.preferred_contact_time else None,
            booking.service_description,
            booking.booking_date,
            booking.booking_time,
            booking.time_of_day.value if booking.time_of_day else None,
            booking.additional_notes,
            booking.status.value
        )
        
        row = await db.fetchrow(query, *values)
        return Booking.model_validate(row)
    
    @staticmethod
    async def get_by_id(booking_id: UUID) -> Optional[Booking]:
        """Get a booking by its ID."""
        query = "SELECT * FROM booking WHERE id = $1"
        row = await db.fetchrow(query, booking_id)
        if row:
            return Booking.model_validate(row)
        return None
    
    @staticmethod
    async def get_by_conversation_id(conversation_id: UUID) -> List[Booking]:
        """Get all bookings for a conversation."""
        query = "SELECT * FROM booking WHERE conversation_id = $1 ORDER BY created_at DESC"
        rows = await db.fetch(query, conversation_id)
        return [Booking.model_validate(row) for row in rows]
    
    @staticmethod
    async def get_by_phone(phone: str) -> List[Booking]:
        """Get all bookings for a phone number."""
        query = "SELECT * FROM booking WHERE phone = $1 ORDER BY created_at DESC"
        rows = await db.fetch(query, phone)
        return [Booking.model_validate(row) for row in rows]
    
    @staticmethod
    async def update(booking_id: UUID, booking_update: BookingUpdate) -> Optional[Booking]:
        """Update a booking."""
        # First check if booking exists
        booking = await BookingRepository.get_by_id(booking_id)
        if not booking:
            return None
        
        # Build update query dynamically based on provided fields
        update_parts = []
        values = [booking_id]  # First parameter is always the booking ID
        param_idx = 2  # Start parameter index at 2
        
        # For each field in the update model, add it to the query if it's not None
        fields = booking_update.model_dump(exclude_none=True)
        for field_name, value in fields.items():
            # Handle enum values
            if isinstance(value, (BookingStatus, TimeOfDay, ContactMethod)):
                value = value.value
                
            update_parts.append(f"{field_name} = ${param_idx}")
            values.append(value)
            param_idx += 1
        
        # If there are no fields to update, return the original booking
        if not update_parts:
            return booking
        
        # Build the complete query
        update_clause = ", ".join(update_parts)
        query = f"UPDATE booking SET {update_clause}, last_updated = NOW() WHERE id = $1 RETURNING *"
        
        # Execute update
        row = await db.fetchrow(query, *values)
        if row:
            return Booking.model_validate(row)
        return None
    
    @staticmethod
    async def delete(booking_id: UUID) -> bool:
        """Delete a booking."""
        query = "DELETE FROM booking WHERE id = $1 RETURNING id"
        result = await db.fetchval(query, booking_id)
        return result is not None
    
    @staticmethod
    async def get_pending_bookings() -> List[Booking]:
        """Get all pending bookings."""
        query = "SELECT * FROM booking WHERE status = $1 ORDER BY created_at ASC"
        rows = await db.fetch(query, BookingStatus.PENDING.value)
        return [Booking.model_validate(row) for row in rows]
    
    @staticmethod
    async def update_status(booking_id: UUID, status: BookingStatus) -> Optional[Booking]:
        """Update a booking's status."""
        query = "UPDATE booking SET status = $1, last_updated = NOW() WHERE id = $2 RETURNING *"
        row = await db.fetchrow(query, status.value, booking_id)
        if row:
            return Booking.model_validate(row)
        return None