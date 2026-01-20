"""
Booking Service Client for communicating with the Booking Agent API
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from models import BookingAgentResponse

logger = logging.getLogger(__name__)

class BookingServiceClient:
    """Client for interacting with the Booking Agent API"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to the Booking Agent"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"📅 Making {method} request to {url}")
            
            if method.upper() == "GET":
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Booking Agent request failed: {e}")
            raise Exception(f"Booking Agent communication error: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error in booking request: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the Booking Agent"""
        try:
            result = await self._make_request("GET", "/api/v1/health")
            logger.info("✅ Booking Agent health check passed")
            return result
        except Exception as e:
            logger.error(f"❌ Booking Agent health check failed: {e}")
            raise
    
    async def book_meeting(self, command: str) -> BookingAgentResponse:
        """Book a meeting using natural language command"""
        try:
            logger.info(f"📅 Booking meeting with command: {command}")
            
            data = {"command": command}
            result = await self._make_request("POST", "/api/v1/book", data)
            
            response = BookingAgentResponse(**result)
            logger.info(f"✅ Booking result: {response.message}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Booking failed: {e}")
            # Return failed response instead of raising
            return BookingAgentResponse(
                success=False,
                message=f"Booking failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def confirm_booking(self, command: str, confirmation: str = "yes") -> BookingAgentResponse:
        """Confirm a booking"""
        try:
            logger.info(f"📅 Confirming booking: {command} -> {confirmation}")
            
            data = {
                "command": command,
                "confirmation": confirmation
            }
            result = await self._make_request("POST", "/api/v1/confirm", data)
            
            response = BookingAgentResponse(**result)
            logger.info(f"✅ Booking confirmation result: {response.message}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Booking confirmation failed: {e}")
            return BookingAgentResponse(
                success=False,
                message=f"Booking confirmation failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def reschedule_meeting(self, command: str) -> BookingAgentResponse:
        """Reschedule a meeting using natural language command"""
        try:
            logger.info(f"🔄 Rescheduling meeting with command: {command}")
            
            data = {"command": command}
            result = await self._make_request("POST", "/api/v1/reschedule", data)
            
            # Convert to BookingAgentResponse format
            response = BookingAgentResponse(
                success=result.get("success", False),
                message=result.get("message", ""),
                events=result.get("events"),  # Use events field for reschedule operations
                operation=result.get("operation", "reschedule"),
                requires_confirmation=result.get("requires_confirmation", False)
            )
            
            logger.info(f"✅ Reschedule result: {response.message}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Reschedule failed: {e}")
            return BookingAgentResponse(
                success=False,
                message=f"Reschedule failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def confirm_reschedule(self, command: str, confirmation: str = "yes") -> BookingAgentResponse:
        """Confirm a reschedule"""
        try:
            logger.info(f"🔄 Confirming reschedule: {command} -> {confirmation}")
            
            data = {
                "command": command,
                "confirmation": confirmation
            }
            result = await self._make_request("POST", "/api/v1/reschedule/confirm", data)
            
            response = BookingAgentResponse(
                success=result.get("success", False),
                message=result.get("message", ""),
                events=result.get("events"),  # Use events field for reschedule operations
                operation=result.get("operation", "reschedule"),
                requires_confirmation=False
            )
            
            logger.info(f"✅ Reschedule confirmation result: {response.message}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Reschedule confirmation failed: {e}")
            return BookingAgentResponse(
                success=False,
                message=f"Reschedule confirmation failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def cancel_meeting(self, command: str) -> BookingAgentResponse:
        """Cancel a meeting using natural language command"""
        try:
            logger.info(f"🗑️ Cancelling meeting with command: {command}")
            
            data = {"command": command}
            result = await self._make_request("POST", "/api/v1/cancel", data)
            
            response = BookingAgentResponse(
                success=result.get("success", False),
                message=result.get("message", ""),
                events=result.get("events"),  # Use events field for cancel operations
                operation=result.get("operation", "cancel"),
                requires_confirmation=result.get("requires_confirmation", False)
            )
            
            logger.info(f"✅ Cancel result: {response.message}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Cancel failed: {e}")
            return BookingAgentResponse(
                success=False,
                message=f"Cancel failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def confirm_cancel(self, command: str, confirmation: str = "yes") -> BookingAgentResponse:
        """Confirm a cancellation"""
        try:
            logger.info(f"🗑️ Confirming cancel: {command} -> {confirmation}")
            
            data = {
                "command": command,
                "confirmation": confirmation
            }
            result = await self._make_request("POST", "/api/v1/cancel/confirm", data)
            
            response = BookingAgentResponse(
                success=result.get("success", False),
                message=result.get("message", ""),
                requires_confirmation=False
            )
            
            logger.info(f"✅ Cancel confirmation result: {response.message}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Cancel confirmation failed: {e}")
            return BookingAgentResponse(
                success=False,
                message=f"Cancel confirmation failed: {str(e)}",
                requires_confirmation=False
            )
    
    async def get_calendar_events(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get calendar events for a date range (if supported by Booking Agent)"""
        try:
            data = {
                "start_date": start_date,
                "end_date": end_date
            }
            result = await self._make_request("POST", "/api/v1/events", data)
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get calendar events: {e}")
            return {"success": False, "message": str(e), "events": []}
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def test_booking_service_connection(base_url: str) -> bool:
    """Test connection to Booking Service"""
    try:
        async with BookingServiceClient(base_url) as client:
            await client.health_check()
            return True
    except Exception as e:
        logger.error(f"❌ Booking Service connection test failed: {e}")
        return False

async def parse_booking_command(command: str) -> Dict[str, Any]:
    """
    Parse a booking command to extract structured information
    This can be enhanced with NLP if needed
    """
    # Basic parsing - can be enhanced with more sophisticated NLP
    import re
    from datetime import datetime
    
    result = {
        "command": command,
        "attendees": [],
        "date_time": None,
        "duration": None,
        "title": None
    }
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, command)
    result["attendees"] = emails
    
    # Extract time patterns
    time_patterns = [
        r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
        r'\b(\d{1,2})\s*(am|pm)\b',
        r'\b(\d{1,2})\.(\d{2})\s*(am|pm)\b'
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            result["time_match"] = match.group()
            break
    
    # Extract duration
    duration_pattern = r'\b(\d+)\s*(min|mins|minutes|hour|hours|hr|hrs)\b'
    duration_match = re.search(duration_pattern, command, re.IGNORECASE)
    if duration_match:
        duration_value = int(duration_match.group(1))
        duration_unit = duration_match.group(2).lower()
        
        if duration_unit in ['hour', 'hours', 'hr', 'hrs']:
            result["duration"] = duration_value * 60
        else:
            result["duration"] = duration_value
    
    return result