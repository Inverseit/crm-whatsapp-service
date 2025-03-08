from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from app.db.repositories.booking import BookingRepository
from app.models.booking import Booking, BookingUpdate, BookingStatus

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("/", response_model=List[Booking])
async def get_bookings(
    status: Optional[str] = Query(None, description="Filter by booking status"),
    phone: Optional[str] = Query(None, description="Filter by phone number")
) -> List[Booking]:
    """
    Get all bookings with optional filters.
    
    Args:
        status: Optional booking status filter
        phone: Optional phone number filter
        
    Returns:
        A list of bookings
    """
    if status == "pending":
        return await BookingRepository.get_pending_bookings()
    elif phone:
        return await BookingRepository.get_by_phone(phone)
    else:
        # This would need to be implemented for production
        # with pagination for large result sets
        raise HTTPException(
            status_code=400, 
            detail="Please provide either a status or phone filter"
        )

@router.get("/{booking_id}", response_model=Booking)
async def get_booking(booking_id: UUID) -> Booking:
    """
    Get a booking by ID.
    
    Args:
        booking_id: The booking ID
        
    Returns:
        The booking, if found
    """
    booking = await BookingRepository.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.put("/{booking_id}", response_model=Booking)
async def update_booking(booking_id: UUID, booking_update: BookingUpdate) -> Booking:
    """
    Update a booking.
    
    Args:
        booking_id: The booking ID
        booking_update: The booking update data
        
    Returns:
        The updated booking
    """
    booking = await BookingRepository.update(booking_id, booking_update)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.put("/{booking_id}/status", response_model=Booking)
async def update_booking_status(
    booking_id: UUID, 
    status: BookingStatus
) -> Booking:
    """
    Update a booking's status.
    
    Args:
        booking_id: The booking ID
        status: The new status
        
    Returns:
        The updated booking
    """
    booking = await BookingRepository.update_status(booking_id, status)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.delete("/{booking_id}")
async def delete_booking(booking_id: UUID) -> dict:
    """
    Delete a booking.
    
    Args:
        booking_id: The booking ID
        
    Returns:
        A success message
    """
    success = await BookingRepository.delete(booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"status": "success", "message": "Booking deleted"}