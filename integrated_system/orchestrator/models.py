"""
Data models for the Integrated Booking & Calling System
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
from enum import Enum

# =============================================================================
# ENUMS
# =============================================================================

class ActionType(str, Enum):
    """Types of actions supported by the system"""
    BOOKING = "booking"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    MANUAL_CALL = "manual_call"

class TransactionState(str, Enum):
    """States of a transaction"""
    CREATED = "created"
    BOOKING_ATTEMPTED = "booking_attempted"
    RESCHEDULE_ATTEMPTED = "reschedule_attempted"
    CANCEL_ATTEMPTED = "cancel_attempted"
    CALL_TRIGGERED = "call_triggered"
    CALL_COMPLETED = "call_completed"
    USER_CONFIRMED = "user_confirmed"
    USER_DECLINED = "user_declined"
    CALL_FAILED = "call_failed"
    COMPLETED = "completed"
    FAILED = "failed"

class CallStatus(str, Enum):
    """Status of phone calls"""
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"

# =============================================================================
# REQUEST MODELS
# =============================================================================

class IntegratedBookingRequest(BaseModel):
    """Request for integrated booking with optional call trigger"""
    booking_command: str = Field(..., description="Natural language booking command")
    trigger_call: bool = Field(default=False, description="Whether to trigger a confirmation call")
    user_phone: Optional[str] = Field(None, description="Phone number for confirmation call")
    call_delay_minutes: int = Field(default=0, description="Minutes to wait before calling")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")

class IntegratedRescheduleRequest(BaseModel):
    """Request for integrated rescheduling with optional call trigger"""
    reschedule_command: str = Field(..., description="Natural language reschedule command")
    trigger_call: bool = Field(default=False, description="Whether to trigger a confirmation call")
    user_phone: Optional[str] = Field(None, description="Phone number for confirmation call")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")

class IntegratedCancelRequest(BaseModel):
    """Request for integrated cancellation with optional call trigger"""
    cancel_command: str = Field(..., description="Natural language cancel command")
    trigger_call: bool = Field(default=False, description="Whether to trigger a confirmation call")
    user_phone: Optional[str] = Field(None, description="Phone number for confirmation call")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")

class ManualCallRequest(BaseModel):
    """Request for manual call trigger"""
    phone_number: str = Field(..., description="Phone number to call")
    message: str = Field(..., description="Message to convey during the call")
    call_type: str = Field(default="manual", description="Type of call")
    user_id: Optional[str] = Field(None, description="User identifier")

# =============================================================================
# RESPONSE MODELS
# =============================================================================

class BookingAgentResponse(BaseModel):
    """Response from Booking Agent API"""
    success: bool
    message: str
    meeting_details: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    available_slots: Optional[List[Dict[str, Any]]] = None
    event_link: Optional[str] = None
    requires_confirmation: bool = False
    event_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None  # For reschedule operations
    operation: Optional[str] = None  # To distinguish between book/reschedule/cancel

class CallingAgentResponse(BaseModel):
    """Response from Calling Agent API"""
    success: bool
    message: str
    call_sid: Optional[str] = None
    call_status: Optional[str] = None
    estimated_duration: Optional[int] = None

class IntegratedBookingResponse(BaseModel):
    """Response for integrated booking workflow"""
    transaction_id: str
    success: bool
    message: str
    booking_result: Optional[BookingAgentResponse] = None
    call_scheduled: bool = False
    estimated_call_time: Optional[int] = None
    next_steps: Optional[List[str]] = None

class IntegratedResponse(BaseModel):
    """Generic response for integrated workflows"""
    transaction_id: str
    success: bool
    message: str
    result: Optional[Dict[str, Any]] = None
    call_scheduled: bool = False
    next_steps: Optional[List[str]] = None

# =============================================================================
# STATE MANAGEMENT MODELS
# =============================================================================

class TransactionStatus(BaseModel):
    """Status of a transaction"""
    transaction_id: str
    action_type: ActionType
    state: TransactionState
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None
    original_request: Dict[str, Any]
    state_history: List[Dict[str, Any]] = []
    call_details: Optional[Dict[str, Any]] = None
    final_result: Optional[Dict[str, Any]] = None

class CallCallback(BaseModel):
    """Callback data from Calling Agent"""
    transaction_id: Optional[str] = None
    call_sid: str
    status: CallStatus
    result: Optional[str] = None
    user_response: Optional[str] = None
    action_required: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    duration: Optional[int] = None

# =============================================================================
# SERVICE CLIENT MODELS
# =============================================================================

class BookingServiceRequest(BaseModel):
    """Request to Booking Service"""
    command: str
    confirmation: Optional[str] = None

class CallTriggerRequest(BaseModel):
    """Request to trigger a call"""
    phone_number: str
    call_type: str = "confirmation"
    context: Dict[str, Any]
    message_template: Optional[str] = None

# =============================================================================
# CONFIGURATION MODELS
# =============================================================================

class GoogleAuthConfig(BaseModel):
    """Google authentication configuration"""
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str] = Field(default_factory=lambda: [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.email'
    ])

class TwilioConfig(BaseModel):
    """Twilio configuration"""
    account_sid: str
    auth_token: str
    phone_number: str
    webhook_base_url: str

class SystemConfig(BaseModel):
    """System-wide configuration"""
    booking_agent_url: str = "http://localhost:8000"
    calling_agent_url: str = "http://localhost:8001"
    orchestrator_port: int = 8080
    state_storage_type: str = "memory"  # "memory", "sqlite", "postgres"
    state_storage_config: Optional[Dict[str, Any]] = None
    google_auth: Optional[GoogleAuthConfig] = None
    twilio: Optional[TwilioConfig] = None
    log_level: str = "INFO"

# =============================================================================
# WEB UI MODELS
# =============================================================================

class UIActionRequest(BaseModel):
    """Request from the web UI"""
    action: Literal["book", "reschedule", "cancel"]
    command: str
    phone_number: Optional[str] = None
    enable_call: bool = False
    call_delay: int = 0
    user_preferences: Optional[Dict[str, Any]] = None

class UIActionResponse(BaseModel):
    """Response to the web UI"""
    success: bool
    transaction_id: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    call_info: Optional[Dict[str, Any]] = None

# =============================================================================
# AUTHENTICATION MODELS
# =============================================================================

class UserSession(BaseModel):
    """User session information"""
    user_id: str
    email: str
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    twilio_authorized: bool = False
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

class AuthRequest(BaseModel):
    """Authentication request"""
    provider: Literal["google", "twilio"]
    code: Optional[str] = None
    state: Optional[str] = None
    redirect_uri: Optional[str] = None

class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    session_id: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None
    requires_additional_auth: bool = False
    auth_url: Optional[str] = None

# =============================================================================
# WEBHOOK MODELS
# =============================================================================

class BookingWebhook(BaseModel):
    """Webhook from Google Calendar/Booking Agent"""
    event_type: str
    event_id: str
    calendar_id: str
    user_email: str
    changes: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class TwilioWebhook(BaseModel):
    """Webhook from Twilio"""
    call_sid: str
    call_status: str
    call_duration: Optional[str] = None
    recording_url: Optional[str] = None
    transcription: Optional[str] = None
    user_input: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# =============================================================================
# UTILITY MODELS
# =============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    service: str
    status: Literal["healthy", "unhealthy", "degraded"]
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None
    dependencies: Optional[Dict[str, str]] = None

class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    message: str
    data: Optional[Any] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# =============================================================================
# NOTIFICATION MODELS
# =============================================================================

class NotificationRequest(BaseModel):
    """Request to send a notification"""
    user_id: str
    type: Literal["sms", "email", "call"]
    message: str
    priority: Literal["low", "medium", "high"] = "medium"
    metadata: Optional[Dict[str, Any]] = None

class NotificationResponse(BaseModel):
    """Response from notification service"""
    notification_id: str
    success: bool
    message: str
    delivery_status: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)