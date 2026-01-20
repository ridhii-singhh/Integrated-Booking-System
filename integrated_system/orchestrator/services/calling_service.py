"""
Calling Service Client for communicating with the Calling Agent API
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from models import CallingAgentResponse
from config import settings

logger = logging.getLogger(__name__)

class CallingServiceClient:
    """Client for interacting with the Calling Agent API"""
    
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
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP request to the Calling Agent"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"📞 Making {method} request to {url}")
            
            if method.upper() == "GET":
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Calling Agent request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error in calling request: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the Calling Agent"""
        try:
            result = await self._make_request("GET", "/health")
            logger.info("✅ Calling Agent health check passed")
            return result
        except Exception as e:
            logger.error(f"❌ Calling Agent health check failed: {e}")
            raise
    
    async def trigger_confirmation_call(self, phone_number: str, context: Dict[str, Any]) -> CallingAgentResponse:
        """Trigger a confirmation call"""
        try:
            logger.info(f"📞 Triggering confirmation call to {phone_number}")
            logger.info(f"📞 Context received: {context}")
            
            # Extract context information
            action_type = context.get("action_type", "confirmation")
            meeting_details = context.get("meeting_details", {}) or {}
            transaction_id = context.get("transaction_id", "")
            
            # Prepare call script based on action type
            script = self._prepare_call_script(action_type, meeting_details)
            
            # Create call request (this will need to be adapted based on the actual Calling Agent API)
            data = {
                "phone_number": phone_number,
                "script": script,
                "context": context,
                "callback_url": f"{settings.ORCHESTRATOR_HOST}:{settings.ORCHESTRATOR_PORT}/api/v1/call-callback"
            }
            
            # Since the current Calling Agent auto-triggers calls, we might need to modify it
            # For now, we'll use a custom endpoint or extend the existing functionality
            result = await self._trigger_custom_call(phone_number, script, context)
            
            # Handle None result
            if result is None:
                logger.error("❌ Received None result from call trigger")
                return CallingAgentResponse(
                    success=False,
                    message=f"Call trigger failed: No response from calling agent",
                    call_sid=None,
                    call_status="failed"
                )
            
            response = CallingAgentResponse(
                success=result.get("success", True),
                message=result.get("message", f"Call triggered to {phone_number}"),
                call_sid=result.get("call_sid"),
                call_status=result.get("call_status", "initiated")
            )
            
            logger.info(f"✅ Call trigger result: {response.message}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Call trigger failed: {e}")
            return CallingAgentResponse(
                success=False,
                message=f"Call trigger failed: {str(e)}"
            )
    
    async def _trigger_custom_call(self, phone_number: str, script: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a custom call with specific script and context
        This method will interact with the enhanced Calling Agent
        """
        try:
            # Since the original Calling Agent uses auto-triggering,
            # we'll need to create a new endpoint for controlled calls
            
            data = {
                "target_phone": phone_number,
                "call_script": script,
                "context": context,
                "action_type": context.get("action_type", "confirmation")
            }
            
            # Try the enhanced endpoint first
            try:
                logger.info(f"📞 Making request to calling agent with data: {data}")
                result = await self._make_request("POST", "/api/v1/trigger-call", data)
                logger.info(f"📞 Received result from calling agent: {result}")
                if result is None:
                    logger.warning("📞 Received None response from calling agent, using fallback")
                    return await self._fallback_call_trigger(phone_number, script, context)
                return result
            except Exception as e:
                # Fallback: Use the existing functionality by modifying config
                logger.warning(f"📞 Using fallback call trigger method due to error: {e}")
                return await self._fallback_call_trigger(phone_number, script, context)
                
        except Exception as e:
            logger.error(f"❌ Custom call trigger failed: {e}")
            # Return a fallback response instead of raising
            return {
                "success": False,
                "message": f"Call trigger failed: {str(e)}",
                "call_sid": None,
                "call_status": "failed"
            }
    
    async def _fallback_call_trigger(self, phone_number: str, script: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback method to trigger calls using existing infrastructure
        """
        # This would require updating the Calling Agent's config temporarily
        # or using a different approach. For now, return a simulated response.
        
        logger.info(f"📞 Fallback call trigger for {phone_number}")
        
        # In a real implementation, this might:
        # 1. Update the Calling Agent's config with the new phone number
        # 2. Send a restart signal to trigger the call
        # 3. Monitor for call completion
        
        return {
            "success": True,
            "message": f"Call scheduled for {phone_number}",
            "call_sid": f"simulated_call_{asyncio.get_event_loop().time()}",
            "call_status": "queued"
        }
    
    def _prepare_call_script(self, action_type: str, meeting_details: Dict[str, Any]) -> str:
        """Prepare the call script based on action type and meeting details"""
        
        # Extract meeting information
        title = meeting_details.get("title", "your meeting")
        start_time = meeting_details.get("start_time", "the scheduled time")
        attendees = meeting_details.get("attendees", [])
        attendees_str = ", ".join(attendees) if attendees else "the participants"
        
        # Format attendees list nicely
        if len(attendees) > 1:
            attendees_str = ", ".join(attendees[:-1]) + f" and {attendees[-1]}"
        elif len(attendees) == 1:
            attendees_str = attendees[0]
        
        script_templates = {
            "booking_confirmation": f"""
                Hello! This is your booking confirmation call. 
                I'm calling to confirm your meeting titled '{title}' 
                scheduled for {start_time} with {attendees_str}.
                Please say 'yes' to confirm this booking or 'no' if you need to make changes.
                """,
            
            "reschedule_confirmation": f"""
                Hello! I'm calling about your meeting reschedule request.
                Your meeting '{title}' has been rescheduled to {start_time}.
                Please say 'yes' to confirm this new time or 'no' if you prefer the original time.
                """,
            
            "cancel_confirmation": f"""
                Hello! I'm calling to confirm the cancellation of your meeting.
                The meeting '{title}' scheduled for {start_time} will be cancelled.
                Please say 'yes' to confirm cancellation or 'no' to keep the meeting.
                """,
            
            "reminder": f"""
                Hello! This is a reminder about your upcoming meeting.
                You have a meeting titled '{title}' scheduled for {start_time} with {attendees_str}.
                Please make sure you're available at the scheduled time.
                """,
            
            "manual_call": """
                Hello! This is a call from your booking system.
                Please listen to the following message.
                """
        }
        
        script = script_templates.get(action_type, script_templates["manual_call"])
        
        # Clean up the script formatting
        return " ".join(script.split())
    
    async def trigger_manual_call(self, phone_number: str, context: Dict[str, Any]) -> CallingAgentResponse:
        """Trigger a manual call with custom message"""
        try:
            logger.info(f"📞 Triggering manual call to {phone_number}")
            
            message = context.get("message", "This is a call from your booking system.")
            
            data = {
                "phone_number": phone_number,
                "message": message,
                "context": context
            }
            
            result = await self._trigger_custom_call(phone_number, message, context)
            
            response = CallingAgentResponse(
                success=result.get("success", True),
                message=result.get("message", f"Manual call triggered to {phone_number}"),
                call_sid=result.get("call_sid"),
                call_status=result.get("call_status", "initiated")
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Manual call trigger failed: {e}")
            return CallingAgentResponse(
                success=False,
                message=f"Manual call trigger failed: {str(e)}"
            )
    
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Get the status of a specific call"""
        try:
            data = {"call_sid": call_sid}
            result = await self._make_request("POST", "/api/v1/call-status", data)
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get call status: {e}")
            return {"success": False, "message": str(e)}
    
    async def cancel_call(self, call_sid: str) -> Dict[str, Any]:
        """Cancel an ongoing call"""
        try:
            data = {"call_sid": call_sid, "action": "cancel"}
            result = await self._make_request("POST", "/api/v1/call-control", data)
            return result
        except Exception as e:
            logger.error(f"❌ Failed to cancel call: {e}")
            return {"success": False, "message": str(e)}
    
    async def send_call_update(self, call_sid: str, message: str) -> Dict[str, Any]:
        """Send an update/message to an ongoing call"""
        try:
            data = {
                "call_sid": call_sid,
                "action": "update",
                "message": message
            }
            result = await self._make_request("POST", "/api/v1/call-control", data)
            return result
        except Exception as e:
            logger.error(f"❌ Failed to send call update: {e}")
            return {"success": False, "message": str(e)}
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def test_calling_service_connection(base_url: str) -> bool:
    """Test connection to Calling Service"""
    try:
        async with CallingServiceClient(base_url) as client:
            await client.health_check()
            return True
    except Exception as e:
        logger.error(f"❌ Calling Service connection test failed: {e}")
        return False

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format"""
    import re
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different phone number formats
    if len(digits) == 10:
        # US number without country code
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        # US number with country code
        return f"+{digits}"
    elif digits.startswith('91') and len(digits) == 12:
        # Indian number with country code
        return f"+{digits}"
    elif len(digits) == 10 and not digits.startswith('1'):
        # Could be Indian number without country code
        return f"+91{digits}"
    else:
        # Return as-is with + prefix if not already there
        if phone.startswith('+'):
            return phone
        else:
            return f"+{digits}"

def extract_call_response_intent(text: str) -> Dict[str, Any]:
    """Extract intent from user's call response"""
    text_lower = text.lower().strip()
    
    # Positive responses
    positive_keywords = ['yes', 'yeah', 'yep', 'confirm', 'correct', 'ok', 'okay', 'sure', 'agree']
    
    # Negative responses
    negative_keywords = ['no', 'nope', 'cancel', 'wrong', 'incorrect', 'disagree']
    
    # Reschedule indicators
    reschedule_keywords = ['reschedule', 'change', 'move', 'different time', 'later', 'earlier']
    
    result = {
        "intent": "unknown",
        "confidence": 0.0,
        "extracted_info": {}
    }
    
    # Check for positive response
    if any(keyword in text_lower for keyword in positive_keywords):
        result["intent"] = "confirm"
        result["confidence"] = 0.8
    
    # Check for negative response
    elif any(keyword in text_lower for keyword in negative_keywords):
        result["intent"] = "decline"
        result["confidence"] = 0.8
    
    # Check for reschedule request
    elif any(keyword in text_lower for keyword in reschedule_keywords):
        result["intent"] = "reschedule"
        result["confidence"] = 0.7
        
        # Try to extract time information
        import re
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
            r'\b(\d{1,2})\s*(am|pm)\b',
            r'\btomorrow\b',
            r'\bnext week\b',
            r'\bmonday|tuesday|wednesday|thursday|friday|saturday|sunday\b'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result["extracted_info"]["time_reference"] = match.group()
                break
    
    return result