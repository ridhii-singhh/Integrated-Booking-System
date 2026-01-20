from fastapi import APIRouter, HTTPException
from models import (
    BookingRequest,
    BookingResponse,
    ConfirmationRequest,
    EventsResponse,
    ReschedulePreviewRequest,
    RescheduleConfirmRequest,
    CancelPreviewRequest,
    CancelConfirmRequest,
)
from booking_service import BookingService
import datetime

router = APIRouter()
booking_service = BookingService()

@router.post("/book", response_model=BookingResponse)
async def book_meeting(request: BookingRequest):
    """
    Book a meeting using natural language command.
    
    Example: "book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins"
    """
    try:
        result = booking_service.process_booking_command(request.command)
        
        return BookingResponse(
            success=result['success'],
            message=result['message'],
            meeting_details=result.get('meeting_details'),
            available_slots=result.get('available_slots'),
            requires_confirmation=result.get('requires_confirmation', False)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Booking failed: {str(e)}")

@router.post("/confirm", response_model=BookingResponse)
async def confirm_booking(request: ConfirmationRequest):
    """
    Confirm and book a meeting after checking availability.
    """
    try:
        result = booking_service.confirm_and_book(request.command, request.confirmation)
        
        return BookingResponse(
            success=result['success'],
            message=result['message'],
            event_link=result.get('event_link'),
            requires_confirmation=False
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "Booking Agent API"
    } 


# ============== Reschedule Endpoints ==============

@router.post("/reschedule", response_model=EventsResponse)
async def reschedule_preview(request: ReschedulePreviewRequest):
    """Parse reschedule command and preview target events before confirmation."""
    try:
        result = booking_service.process_reschedule_command(request.command)
        return EventsResponse(
            success=result['success'],
            message=result['message'],
            events=result.get('events'),
            requires_confirmation=result.get('requires_confirmation', False),
            operation='reschedule',
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reschedule failed: {str(e)}")


@router.post("/reschedule/confirm", response_model=EventsResponse)
async def reschedule_confirm(request: RescheduleConfirmRequest):
    """Confirm and perform rescheduling of events from the command."""
    try:
        confirmation = request.confirmation or "no"
        result = booking_service.confirm_and_reschedule(request.command, confirmation)
        return EventsResponse(
            success=result['success'],
            message=result['message'],
            events=result.get('updated_events'),
            requires_confirmation=False,
            operation='reschedule',
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reschedule confirmation failed: {str(e)}")


# ============== Cancel Endpoints ==============

@router.post("/cancel", response_model=EventsResponse)
async def cancel_preview(request: CancelPreviewRequest):
    """Parse cancel command and preview target events before confirmation."""
    try:
        result = booking_service.process_cancel_command(request.command)
        return EventsResponse(
            success=result['success'],
            message=result['message'],
            events=result.get('events'),
            requires_confirmation=result.get('requires_confirmation', False),
            operation='cancel',
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancel failed: {str(e)}")


@router.post("/cancel/confirm", response_model=EventsResponse)
async def cancel_confirm(request: CancelConfirmRequest):
    """Confirm and perform cancellation of events from the command."""
    try:
        confirmation = request.confirmation or "no"
        result = booking_service.confirm_and_cancel(request.command, confirmation)
        return EventsResponse(
            success=result['success'],
            message=result['message'],
            events=None,
            requires_confirmation=False,
            operation='cancel',
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancel confirmation failed: {str(e)}")