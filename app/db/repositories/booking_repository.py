from uuid import UUID
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, time

from app.db.models import Booking, BookingStatus, TimeOfDay, ContactMethod

class BookingRepository:
    """Repository for booking data access operations."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        conversation_id: UUID,
        client_name: str,
        phone: str,
        service_description: str,
        preferred_contact_method: ContactMethod,
        use_phone_for_whatsapp: bool = True,
        whatsapp: Optional[str] = None,
        preferred_contact_time: Optional[TimeOfDay] = None,
        booking_date: Optional[date] = None,
        booking_time: Optional[time] = None,
        time_of_day: Optional[TimeOfDay] = None,
        additional_notes: Optional[str] = None,
        status: BookingStatus = BookingStatus.PENDING
    ) -> Booking:
        """Create a new booking in the database."""
        booking = Booking(
            conversation_id=conversation_id,
            client_name=client_name,
            phone=phone,
            use_phone_for_whatsapp=use_phone_for_whatsapp,
            whatsapp=whatsapp or phone if use_phone_for_whatsapp else None,
            preferred_contact_method=preferred_contact_method,
            preferred_contact_time=preferred_contact_time,
            service_description=service_description,
            booking_date=booking_date,
            booking_time=booking_time,
            time_of_day=time_of_day,
            additional_notes=additional_notes,
            status=status
        )
        
        session.add(booking)
        await session.flush()
        return booking
    
    @staticmethod
    async def get_by_id(session: AsyncSession, booking_id: UUID) -> Optional[Booking]:
        """Get a booking by its ID."""
        result = await session.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def get_by_conversation_id(session: AsyncSession, conversation_id: UUID) -> List[Booking]:
        """Get all bookings for a conversation."""
        result = await session.execute(
            select(Booking)
            .where(Booking.conversation_id == conversation_id)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_phone(session: AsyncSession, phone: str) -> List[Booking]:
        """Get all bookings for a phone number."""
        result = await session.execute(
            select(Booking)
            .where(Booking.phone == phone)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update(session: AsyncSession, booking_id: UUID, **kwargs) -> Optional[Booking]:
        """Update a booking."""
        booking = await BookingRepository.get_by_id(session, booking_id)
        if not booking:
            return None
            
        for key, value in kwargs.items():
            if hasattr(booking, key):
                setattr(booking, key, value)
                
        session.add(booking)
        await session.flush()
        return booking
    
    @staticmethod
    async def delete(session: AsyncSession, booking_id: UUID) -> bool:
        """Delete a booking."""
        booking = await BookingRepository.get_by_id(session, booking_id)
        if not booking:
            return False
            
        await session.delete(booking)
        await session.flush()
        return True
    
    @staticmethod
    async def get_pending_bookings(session: AsyncSession) -> List[Booking]:
        """Get all pending bookings."""
        result = await session.execute(
            select(Booking)
            .where(Booking.status == BookingStatus.PENDING)
            .order_by(Booking.created_at.asc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_status(
        session: AsyncSession, 
        booking_id: UUID, 
        status: BookingStatus
    ) -> Optional[Booking]:
        """Update a booking's status."""
        booking = await BookingRepository.get_by_id(session, booking_id)
        if not booking:
            return None
            
        booking.status = status
        session.add(booking)
        await session.flush()
        return booking