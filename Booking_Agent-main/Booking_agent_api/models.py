from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class BookingRequest(BaseModel):
    """Request model for booking a meeting with natural language command"""
    command: str = Field(..., description="Natural language command like 'book a progress meeting with tejalr2125@gmail.com on next tuesday 5.00 pm for 30 mins'")

class BookingResponse(BaseModel):
    """Response model for booking operations"""
    success: bool
    message: str
    meeting_details: Optional[dict] = None
    available_slots: Optional[List[dict]] = None
    event_link: Optional[str] = None
    requires_confirmation: bool = False
    event_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class ConfirmationRequest(BaseModel):
    """Request model for confirming a booking"""
    command: str
    confirmation: str = Field(..., description="'yes' or 'no' to confirm booking")


class CommandTypeResponse(BaseModel):
    command_type: Literal["book", "reschedule", "cancel"]


class RescheduleRequest(BaseModel):
    """Request model for rescheduling meetings based on natural language."""
    command: str = Field(..., description="e.g., 'Reschedule all meetings of 8th aug 2025 to 9th aug at 1pm'")
    confirmation: Optional[str] = Field(None, description="'yes' or 'no' to confirm rescheduling")


class CancelRequest(BaseModel):
    """Request model for cancelling meetings based on natural language."""
    command: str = Field(..., description="e.g., 'Cancel my meeting which is at 8pm on 15th aug 2025'")
    confirmation: Optional[str] = Field(None, description="'yes' or 'no' to confirm cancellation")


class EventsResponse(BaseModel):
    success: bool
    message: str
    events: Optional[List[dict]] = None
    requires_confirmation: bool = False
    operation: Optional[str] = None


# Separate models for better OpenAPI docs
class ReschedulePreviewRequest(BaseModel):
    command: str = Field(..., description="Natural language reschedule command")


class RescheduleConfirmRequest(BaseModel):
    command: str = Field(..., description="Same reschedule command used in preview")
    confirmation: Literal["yes", "no"] = Field(..., description="Confirm rescheduling: 'yes' or 'no'")


class CancelPreviewRequest(BaseModel):
    command: str = Field(..., description="Natural language cancel command")


class CancelConfirmRequest(BaseModel):
    command: str = Field(..., description="Same cancel command used in preview")
    confirmation: Literal["yes", "no"] = Field(..., description="Confirm cancellation: 'yes' or 'no'")

class MeetingDetails(BaseModel):
    """Model for parsed meeting details"""
    title: str = Field(..., description="The title of the meeting.")
    attendees: List[str] = Field(..., description="The email addresses of the attendees.")
    date: str = Field(..., description="The date of the meeting. This can be a relative date like 'today' or 'next Friday'.")
    time: str = Field(..., description="The time of the meeting in HH:MM 24-hour format.")
    duration: int = Field(..., description="The duration of the meeting in minutes.")

class AvailableSlot(BaseModel):
    """Model for available time slots"""
    start_time: datetime
    end_time: datetime
    is_available: bool
    display_time: str 