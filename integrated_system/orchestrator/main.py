
"""
Integrated Booking and Calling System Orchestrator
This service coordinates between the Booking Agent and Calling Agent
"""
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Cookie, Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from datetime import datetime
from typing import List
from models import *
from services.booking_service import BookingServiceClient
from services.calling_service import CallingServiceClient
from services.state_manager import StateManager
from services.auth_service import auth_service
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
state_manager = StateManager()
booking_client = BookingServiceClient(settings.BOOKING_AGENT_URL)
calling_client = CallingServiceClient(settings.CALLING_AGENT_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Integrated Booking & Calling System")
    
    # Initialize state manager
    await state_manager.initialize()
    
    # Health checks for dependent services
    try:
        booking_health = await booking_client.health_check()
        logger.info(f"📅 Booking Agent: {booking_health}")
    except Exception as e:
        logger.warning(f"⚠️ Booking Agent health check failed: {e}")
    
    try:
        calling_health = await calling_client.health_check()
        logger.info(f"📞 Calling Agent: {calling_health}")
    except Exception as e:
        logger.warning(f"⚠️ Calling Agent health check failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down Integrated System")
    await state_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Integrated Booking & Calling System",
    description="End-to-end system that connects Google Calendar booking with Twilio calling",
    version="1.0.0",
    lifespan=lifespan
)

# Utility: safely convert nested objects to plain dict
def to_plain_dict(obj):
    try:
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if isinstance(obj, (list, tuple)):
            return [to_plain_dict(x) for x in obj]
        if isinstance(obj, dict):
            return {k: to_plain_dict(v) for k, v in obj.items()}
        # Fallback: best-effort JSON default
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return str(obj)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_ui():
    """Serve the main web interface"""
    return FileResponse("static/index.html")

# =============================================================================
# CORE INTEGRATION ENDPOINTS
# =============================================================================

@app.post("/api/v1/integrated-booking")
async def integrated_booking(request: IntegratedBookingRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint for integrated booking workflow:
    1. Process booking request via Booking Agent
    2. Trigger confirmation call via Calling Agent
    3. Track state and sync updates
    """
    try:
        # Generate unique transaction ID
        transaction_id = await state_manager.create_transaction(
            action_type="booking",
            user_request=request.dict()
        )
        
        logger.info(f"🎯 Starting integrated booking transaction: {transaction_id}")
        
        # Step 1: Process booking with Booking Agent
        booking_result = await booking_client.book_meeting(request.booking_command)
        
        # Update state (store plain dict)
        await state_manager.update_transaction(
            transaction_id, 
            "booking_attempted",
            {"booking_result": to_plain_dict(booking_result)}
        )
        
        if not booking_result.success:
            return JSONResponse(content={
                "transaction_id": transaction_id,
                "success": False,
                "message": f"Booking failed: {booking_result.message}",
                "booking_result": to_plain_dict(booking_result)
            })

       # Auto-confirm if Booking Agent requires confirmation
        if getattr(booking_result, "requires_confirmation", False):
            logger.info("✅ Auto-confirming booking as requires_confirmation=True")
            confirm_result = await booking_client.confirm_booking(request.booking_command, "yes")

            # Mark confirmation result in state with valid states
            if getattr(confirm_result, "success", False):
                await state_manager.update_transaction(
                    transaction_id,
                    "completed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                booking_result = confirm_result
            else:
                await state_manager.update_transaction(
                    transaction_id,
                    "failed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                return JSONResponse(content={
                    "transaction_id": transaction_id,
                    "success": False,
                    "message": f"Booking confirmation failed: {getattr(confirm_result,'message','')}",
                    "booking_result": to_plain_dict(confirm_result)
                })

        # Step 2: Schedule confirmation call if requested
        if request.trigger_call and request.user_phone:
            background_tasks.add_task(
                schedule_confirmation_call,
                transaction_id,
                request.user_phone,
                booking_result,
                request.call_delay_minutes
            )
            
            call_message = f" Confirmation call scheduled for {request.user_phone}"
        else:
            call_message = " No call scheduled"
        
        # Step 3: Return integrated response
        return JSONResponse(content={
            "transaction_id": transaction_id,
            "success": True,
            "message": f"Booking successful! {call_message}",
            "booking_result": to_plain_dict(booking_result),
            "call_scheduled": request.trigger_call,
            "estimated_call_time": request.call_delay_minutes
        })
        
    except Exception as e:
        logger.error(f"❌ Integrated booking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/integrated-reschedule")
async def integrated_reschedule(request: IntegratedRescheduleRequest, background_tasks: BackgroundTasks):
    """Integrated reschedule workflow with optional call confirmation"""
    try:
        transaction_id = await state_manager.create_transaction(
            action_type="reschedule",
            user_request=request.dict()
        )
        
        logger.info(f"🔄 Starting integrated reschedule transaction: {transaction_id}")
        
        # Process reschedule with Booking Agent
        reschedule_result = await booking_client.reschedule_meeting(request.reschedule_command)
        
        await state_manager.update_transaction(
            transaction_id,
            "reschedule_attempted", 
            {"reschedule_result": to_plain_dict(reschedule_result)}
        )
        
        if not reschedule_result.success:
            return JSONResponse(content={
                "transaction_id": transaction_id,
                "success": False,
                "message": f"Reschedule failed: {reschedule_result.message}",
                "result": to_plain_dict(reschedule_result)
            })

        # Auto-confirm if reschedule requires confirmation
        if getattr(reschedule_result, "requires_confirmation", False):
            logger.info("✅ Auto-confirming reschedule as requires_confirmation=True")
            confirm_result = await booking_client.confirm_reschedule(request.reschedule_command, "yes")

            # Mark confirmation result in state
            if getattr(confirm_result, "success", False):
                await state_manager.update_transaction(
                    transaction_id,
                    "completed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                reschedule_result = confirm_result
            else:
                await state_manager.update_transaction(
                    transaction_id,
                    "failed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                return JSONResponse(content={
                    "transaction_id": transaction_id,
                    "success": False,
                    "message": f"Reschedule confirmation failed: {getattr(confirm_result,'message','')}",
                    "result": to_plain_dict(confirm_result)
                })
        
        # Schedule confirmation call if requested
        if request.trigger_call and request.user_phone:
            background_tasks.add_task(
                schedule_reschedule_call,
                transaction_id,
                request.user_phone,
                reschedule_result
            )
            call_message = f" Confirmation call scheduled for {request.user_phone}"
        else:
            call_message = " No call scheduled"
        
        return JSONResponse(content={
            "transaction_id": transaction_id,
            "success": True,
            "message": f"Reschedule successful! {call_message}",
            "result": to_plain_dict(reschedule_result),
            "call_scheduled": request.trigger_call
        })
        
    except Exception as e:
        logger.error(f"❌ Integrated reschedule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/integrated-cancel") 
async def integrated_cancel(request: IntegratedCancelRequest, background_tasks: BackgroundTasks):
    """Integrated cancel workflow with optional call confirmation"""
    try:
        transaction_id = await state_manager.create_transaction(
            action_type="cancel",
            user_request=request.dict()
        )
        
        logger.info(f"🗑️ Starting integrated cancel transaction: {transaction_id}")
        
        # Process cancellation with Booking Agent
        cancel_result = await booking_client.cancel_meeting(request.cancel_command)
        
        await state_manager.update_transaction(
            transaction_id,
            "cancel_attempted",
            {"cancel_result": to_plain_dict(cancel_result)}
        )
        
        if not cancel_result.success:
            return JSONResponse(content={
                "transaction_id": transaction_id,
                "success": False, 
                "message": f"Cancel failed: {cancel_result.message}",
                "result": to_plain_dict(cancel_result)
            })

        # Auto-confirm if cancel requires confirmation
        if getattr(cancel_result, "requires_confirmation", False):
            logger.info("✅ Auto-confirming cancel as requires_confirmation=True")
            confirm_result = await booking_client.confirm_cancel(request.cancel_command, "yes")

            # Mark confirmation result in state
            if getattr(confirm_result, "success", False):
                await state_manager.update_transaction(
                    transaction_id,
                    "completed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                cancel_result = confirm_result
            else:
                await state_manager.update_transaction(
                    transaction_id,
                    "failed",  # valid TransactionState
                    {"confirmation_result": to_plain_dict(confirm_result)}
                )
                return JSONResponse(content={
                    "transaction_id": transaction_id,
                    "success": False,
                    "message": f"Cancel confirmation failed: {getattr(confirm_result,'message','')}",
                    "result": to_plain_dict(confirm_result)
                })
        else:
            # If no confirmation required, mark as completed directly
            await state_manager.update_transaction(
                transaction_id,
                "completed",
                {"cancel_result": to_plain_dict(cancel_result)}
            )
        
        # Schedule confirmation call if requested
        if request.trigger_call and request.user_phone:
            background_tasks.add_task(
                schedule_cancel_call,
                transaction_id,
                request.user_phone,
                cancel_result
            )
            call_message = f" Confirmation call scheduled for {request.user_phone}"
        else:
            call_message = " No call scheduled"
        
        return JSONResponse(content={
            "transaction_id": transaction_id,
            "success": True,
            "message": f"Cancellation successful! {call_message}",
            "result": to_plain_dict(cancel_result),
            "call_scheduled": request.trigger_call
        })
        
    except Exception as e:
        logger.error(f"❌ Integrated cancel failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# BACKGROUND CALL TASKS
# =============================================================================

async def schedule_confirmation_call(transaction_id: str, phone: str, booking_result, delay_minutes: int = 0):
    """Schedule a confirmation call for a booking"""
    try:
        if delay_minutes > 0:
            logger.info(f"⏰ Waiting {delay_minutes} minutes before calling {phone}")
            await asyncio.sleep(delay_minutes * 60)
        
        logger.info(f"📞 Triggering confirmation call for transaction: {transaction_id}")
        
        # Prepare call context
        call_context = {
            "transaction_id": transaction_id,
            "action_type": "booking_confirmation",
            "meeting_details": booking_result.meeting_details,
            "user_phone": phone
        }
        
        # Trigger call via Calling Agent
        call_result = await calling_client.trigger_confirmation_call(phone, call_context)
        
        # Update state
        await state_manager.update_transaction(
            transaction_id,
            "call_triggered",
            {"call_result": call_result.dict() if call_result else None}
        )
        
        logger.info(f"✅ Confirmation call triggered successfully for {phone}")
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger confirmation call: {e}")
        await state_manager.update_transaction(
            transaction_id,
            "call_failed",
            {"error": str(e)}
        )

async def schedule_reschedule_call(transaction_id: str, phone: str, reschedule_result):
    """Schedule a confirmation call for a reschedule"""
    try:
        logger.info(f"📞 Triggering reschedule confirmation call for: {transaction_id}")
        
        call_context = {
            "transaction_id": transaction_id,
            "action_type": "reschedule_confirmation", 
            "events": reschedule_result.events,
            "user_phone": phone
        }
        
        call_result = await calling_client.trigger_confirmation_call(phone, call_context)
        
        await state_manager.update_transaction(
            transaction_id,
            "call_triggered",
            {"call_result": call_result.dict() if call_result else None}
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger reschedule call: {e}")

async def schedule_cancel_call(transaction_id: str, phone: str, cancel_result):
    """Schedule a confirmation call for a cancellation"""
    try:
        logger.info(f"📞 Triggering cancel confirmation call for: {transaction_id}")
        
        call_context = {
            "transaction_id": transaction_id,
            "action_type": "cancel_confirmation",
            "events": cancel_result.events,
            "user_phone": phone
        }
        
        call_result = await calling_client.trigger_confirmation_call(phone, call_context)
        
        await state_manager.update_transaction(
            transaction_id,
            "call_triggered", 
            {"call_result": call_result.dict() if call_result else None}
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger cancel call: {e}")

# =============================================================================
# STATUS AND MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/v1/transaction/{transaction_id}", response_model=TransactionStatus)
async def get_transaction_status(transaction_id: str):
    """Get the status of a transaction"""
    try:
        status = await state_manager.get_transaction_status(transaction_id)
        if not status:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/transactions", response_model=List[TransactionStatus])
async def list_transactions(limit: int = 50, offset: int = 0):
    """List recent transactions"""
    try:
        return await state_manager.list_transactions(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/call-callback")
async def handle_call_callback(callback: CallCallback):
    """Handle callbacks from the Calling Agent"""
    try:
        logger.info(f"📞 Call callback received: {callback.dict()}")
        
        # Update transaction state based on call result
        if callback.transaction_id:
            await state_manager.update_transaction(
                callback.transaction_id,
                "call_completed",
                {
                    "call_status": callback.status,
                    "call_result": callback.result,
                    "user_response": callback.user_response
                }
            )
            
            # If user provided input during call, update booking accordingly
            if callback.user_response and callback.action_required:
                await handle_user_call_response(callback)
        
        return {"status": "callback_processed"}
        
    except Exception as e:
        logger.error(f"❌ Call callback processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_user_call_response(callback: CallCallback):
    """Process user responses received during phone calls"""
    try:
        logger.info(f"🎤 Processing user call response for transaction: {callback.transaction_id}")
        
        transaction = await state_manager.get_transaction_status(callback.transaction_id)
        if not transaction:
            logger.error("Transaction not found for call response")
            return
        
        # Handle different types of user responses
        if callback.action_required == "reschedule_confirmation":
            if "yes" in callback.user_response.lower():
                # Confirm the reschedule
                await booking_client.confirm_reschedule(transaction.original_request)
                await state_manager.update_transaction(
                    callback.transaction_id,
                    "user_confirmed",
                    {"action": "reschedule_confirmed"}
                )
            elif "no" in callback.user_response.lower():
                await state_manager.update_transaction(
                    callback.transaction_id,
                    "user_declined",
                    {"action": "reschedule_declined"}
                )
        
        elif callback.action_required == "cancel_confirmation":
            if "yes" in callback.user_response.lower():
                await booking_client.confirm_cancel(transaction.original_request)
                await state_manager.update_transaction(
                    callback.transaction_id,
                    "user_confirmed",
                    {"action": "cancel_confirmed"}
                )
        
        # Add more response handling as needed
        
    except Exception as e:
        logger.error(f"❌ User call response processing failed: {e}")

@app.get("/api/v1/health")
async def health_check():
    """Comprehensive health check for the integrated system"""
    try:
        health_status = {
            "orchestrator": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # Check Booking Agent
        try:
            booking_health = await booking_client.health_check()
            health_status["services"]["booking_agent"] = "healthy"
        except Exception as e:
            health_status["services"]["booking_agent"] = f"unhealthy: {str(e)}"
        
        # Check Calling Agent
        try:
            calling_health = await calling_client.health_check()
            health_status["services"]["calling_agent"] = "healthy"
        except Exception as e:
            health_status["services"]["calling_agent"] = f"unhealthy: {str(e)}"
        
        # Check State Manager
        try:
            await state_manager.health_check()
            health_status["services"]["state_manager"] = "healthy"
        except Exception as e:
            health_status["services"]["state_manager"] = f"unhealthy: {str(e)}"
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# MANUAL TRIGGER ENDPOINTS (for testing/admin)
# =============================================================================

@app.post("/api/v1/manual-call")
async def manual_call_trigger(request: ManualCallRequest):
    """Manually trigger a call (for testing/admin purposes)"""
    try:
        logger.info(f"📞 Manual call trigger to {request.phone_number}")
        
        call_context = {
            "action_type": "manual_call",
            "message": request.message,
            "user_phone": request.phone_number
        }
        
        result = await calling_client.trigger_manual_call(request.phone_number, call_context)
        
        return {
            "success": True,
            "message": f"Call triggered to {request.phone_number}",
            "call_result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Manual call trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), session_id: str = Cookie(None)):
    """Get current authenticated user"""
    # Try JWT token first
    if credentials:
        payload = auth_service.verify_jwt_token(credentials.credentials)
        if payload:
            return payload
    
    # Try session cookie
    if session_id:
        session = await auth_service.get_user_session(session_id)
        if session:
            return {"user_id": session.user_id, "email": session.email}
    
    return None

async def require_auth(current_user = Depends(get_current_user)):
    """Require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

@app.get("/auth/google")
async def google_auth(redirect_uri: str = None):
    """Initiate Google OAuth flow"""
    try:
        auth_url = await auth_service.get_google_auth_url(state=redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/google/callback")
async def google_auth_callback(code: str, state: str = None, response: FastAPIResponse = None):
    """Handle Google OAuth callback"""
    try:
        auth_result = await auth_service.handle_google_callback(code, state)
        
        if auth_result.success:
            # Set session cookie
            response = RedirectResponse(url="/?auth=success")
            response.set_cookie(
                key="session_id",
                value=auth_result.session_id,
                max_age=settings.SESSION_EXPIRE_HOURS * 3600,
                httponly=True,
                secure=settings.is_production()
            )
            return response
        else:
            return RedirectResponse(url=f"/?auth=error&message={auth_result.message}")
            
    except Exception as e:
        return RedirectResponse(url=f"/?auth=error&message={str(e)}")

@app.post("/auth/logout")
async def logout(response: FastAPIResponse, session_id: str = Cookie(None)):
    """Logout user"""
    if session_id:
        await auth_service.revoke_session(session_id)
    
    response = {"success": True, "message": "Logged out successfully"}
    # Clear cookie
    response.delete_cookie("session_id")
    return response

@app.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user

@app.get("/auth/stats")
async def get_auth_stats():
    """Get authentication statistics"""
    stats = await auth_service.get_session_stats()
    return stats

# =============================================================================
# PROTECTED ENDPOINTS (Optional - can be enabled for production)
# =============================================================================

# Uncomment these decorators to require authentication for main endpoints
# @app.post("/api/v1/integrated-booking", response_model=IntegratedBookingResponse, dependencies=[Depends(require_auth)])
# @app.post("/api/v1/integrated-reschedule", response_model=IntegratedResponse, dependencies=[Depends(require_auth)])
# @app.post("/api/v1/integrated-cancel", response_model=IntegratedResponse, dependencies=[Depends(require_auth)])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
