"""
Enhanced Calling Agent with Orchestrator Integration
Extends the original calling agent to support coordinated calls from the orchestrator
"""
import asyncio
import os
import json
import base64
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import aiohttp

# Import original modules
import sys
sys.path.append('/Users/akash.yadav/Documents/Project/Final-Caller_Agent-main/Caller_Agent')

from config import BASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
from whisper_transcriber import transcribe_audio
from groq_llm import get_llm_response
from free_tts import text_to_speech
from utils import save_ulaw_as_wav, mp3_to_wav, redirect_call_to_play
from call_trigger import trigger_call
from websocket_audio_player import speak_via_twiml_say, play_audio_via_twiml_update, check_call_status
from reliable_audio_solution import (
    deliver_immediate_response, 
    set_current_call_sid, 
    start_response_processor,
    create_listening_twiml
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced models for orchestrator integration
class CallTriggerRequest(BaseModel):
    target_phone: str
    call_script: str
    context: Dict[str, Any]
    action_type: str = "confirmation"
    callback_url: Optional[str] = None

class CallControlRequest(BaseModel):
    call_sid: str
    action: str  # "cancel", "update", "status"
    message: Optional[str] = None

class CallStatusResponse(BaseModel):
    call_sid: str
    status: str
    success: bool
    message: str

# Global state for enhanced features
current_call_context = {}
orchestrator_callback_url = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Enhanced Calling Agent with Orchestrator Integration")
    
    # Don't auto-trigger calls in enhanced mode - wait for orchestrator commands
    logger.info("📞 Enhanced mode: Waiting for orchestrator commands")
    
    yield
    
    logger.info("🛑 Shutting down Enhanced Calling Agent")

app = FastAPI(
    title="Enhanced Calling Agent",
    description="AI Voice Agent with Orchestrator Integration",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# ENHANCED INTEGRATION ENDPOINTS
# =============================================================================

@app.post("/api/v1/trigger-call", response_model=CallStatusResponse)
async def trigger_custom_call(request: CallTriggerRequest, background_tasks: BackgroundTasks):
    """Trigger a custom call with specific script and context"""
    global current_call_context, orchestrator_callback_url
    
    try:
        logger.info(f"📞 Triggering custom call to {request.target_phone}")
        
        # Store call context for use during the call
        current_call_context = {
            "target_phone": request.target_phone,
            "script": request.call_script,
            "context": request.context,
            "action_type": request.action_type,
            "transaction_id": request.context.get("transaction_id")
        }
        
        # Store callback URL
        if request.callback_url:
            orchestrator_callback_url = request.callback_url
        
        # Trigger the call with the target phone number
        call_sid = trigger_call(target_phone=request.target_phone)
        
        # Start response processor
        start_response_processor()
        
        return CallStatusResponse(
            call_sid=call_sid,
            status="initiated",
            success=True,
            message=f"Call triggered successfully to {request.target_phone}"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger custom call: {e}")
        return CallStatusResponse(
            call_sid="",
            status="failed",
            success=False,
            message=f"Failed to trigger call: {str(e)}"
        )

@app.post("/api/v1/call-control", response_model=CallStatusResponse)
async def control_call(request: CallControlRequest):
    """Control an active call"""
    try:
        if request.action == "status":
            is_active, status = check_call_status(request.call_sid)
            return CallStatusResponse(
                call_sid=request.call_sid,
                status=status,
                success=True,
                message=f"Call status: {status}"
            )
        
        elif request.action == "update" and request.message:
            success = await speak_via_twiml_say(request.call_sid, request.message)
            return CallStatusResponse(
                call_sid=request.call_sid,
                status="updated" if success else "failed",
                success=success,
                message="Call updated" if success else "Failed to update call"
            )
        
        elif request.action == "cancel":
            # This would require Twilio API call to end the call
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            try:
                call = client.calls(request.call_sid).update(status='completed')
                return CallStatusResponse(
                    call_sid=request.call_sid,
                    status="cancelled",
                    success=True,
                    message="Call cancelled successfully"
                )
            except Exception as e:
                return CallStatusResponse(
                    call_sid=request.call_sid,
                    status="failed",
                    success=False,
                    message=f"Failed to cancel call: {str(e)}"
                )
        
        else:
            return CallStatusResponse(
                call_sid=request.call_sid,
                status="failed",
                success=False,
                message="Invalid action or missing parameters"
            )
            
    except Exception as e:
        logger.error(f"❌ Call control failed: {e}")
        return CallStatusResponse(
            call_sid=request.call_sid,
            status="failed",
            success=False,
            message=str(e)
        )

async def send_callback_to_orchestrator(call_sid: str, status: str, result: Optional[str] = None, user_response: Optional[str] = None):
    """Send callback to orchestrator about call results"""
    global orchestrator_callback_url, current_call_context
    
    if not orchestrator_callback_url:
        logger.warning("📞 No orchestrator callback URL configured")
        return
    
    try:
        callback_data = {
            "transaction_id": current_call_context.get("transaction_id"),
            "call_sid": call_sid,
            "status": status,
            "result": result,
            "user_response": user_response,
            "action_required": current_call_context.get("action_type"),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(orchestrator_callback_url, json=callback_data) as response:
                if response.status == 200:
                    logger.info("✅ Callback sent to orchestrator successfully")
                else:
                    logger.error(f"❌ Orchestrator callback failed: {response.status}")
                    
    except Exception as e:
        logger.error(f"❌ Failed to send callback to orchestrator: {e}")

# =============================================================================
# ENHANCED CALL HANDLING (Override original endpoints)
# =============================================================================

@app.post("/outgoing-call")
async def generate_enhanced_twiml(request: Request):
    """Enhanced TwiML generation with context-aware responses"""
    global current_call_context
    
    logger.info("📞 Enhanced call connected — sending context-aware TwiML")
    
    # Clean up old files
    for file in ["response.wav", "response.mp3", "caller.wav"]:
        if os.path.exists(file):
            os.remove(file)

    try:
        hostname = BASE_URL.split("://")[1]
    except IndexError:
        logger.error("❌ BASE_URL in config.py seems to be incorrect.")
        return Response(status_code=500)

    start_response_processor()

    # If we have a custom script from orchestrator, use it
    if current_call_context and "script" in current_call_context:
        script = current_call_context["script"]
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">{script}</Say>
            <Gather input="speech" action="{BASE_URL}/handle-enhanced-speech" speechTimeout="3" language="en-US">
                <Say voice="alice">Please respond.</Say>
            </Gather>
            <Redirect>{BASE_URL}/continue-listening</Redirect>
        </Response>"""
    else:
        # Use default TwiML
        twiml = create_listening_twiml()
    
    return Response(content=twiml, media_type="application/xml")

@app.post("/handle-enhanced-speech")
async def handle_enhanced_speech(request: Request):
    """Enhanced speech handling with orchestrator integration"""
    global current_call_context
    
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    call_sid = form_data.get("CallSid", "")
    
    logger.info(f"🎤 Enhanced speech from Gather: '{speech_result}'")
    
    if speech_result and len(speech_result.strip()) > 2:
        # Send callback to orchestrator with user response
        await send_callback_to_orchestrator(
            call_sid=call_sid,
            status="completed",
            result="speech_received",
            user_response=speech_result
        )
        
        # Generate context-aware response
        if current_call_context:
            action_type = current_call_context.get("action_type", "confirmation")
            
            # Create response based on user input and action type
            response_text = generate_context_response(speech_result, action_type)
            
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="alice">{response_text}</Say>
                <Say voice="alice">Thank you for your response. Goodbye!</Say>
            </Response>"""
        else:
            # Fallback to original behavior
            success = await deliver_immediate_response(speech_result, get_llm_response)
            
            if not success:
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                    <Say voice="alice">I'm sorry, I didn't catch that. Please try again.</Say>
                    <Redirect>{BASE_URL}/continue-listening</Redirect>
                </Response>"""
            else:
                twiml = create_listening_twiml()
    else:
        twiml = create_listening_twiml()
    
    return Response(content=twiml.strip(), media_type="application/xml")

def generate_context_response(user_input: str, action_type: str) -> str:
    """Generate contextual response based on user input and action type"""
    user_input_lower = user_input.lower().strip()
    
    # Positive responses
    if any(word in user_input_lower for word in ['yes', 'yeah', 'confirm', 'correct', 'ok', 'sure']):
        responses = {
            "booking_confirmation": "Great! Your meeting has been confirmed. You'll receive a calendar invitation shortly.",
            "reschedule_confirmation": "Perfect! Your meeting has been rescheduled. The calendar will be updated.",
            "cancel_confirmation": "Understood. Your meeting has been cancelled and removed from the calendar."
        }
        return responses.get(action_type, "Thank you for confirming.")
    
    # Negative responses
    elif any(word in user_input_lower for word in ['no', 'cancel', 'wrong', 'incorrect']):
        responses = {
            "booking_confirmation": "I understand. The booking will not be confirmed. Please contact us to reschedule.",
            "reschedule_confirmation": "Got it. The meeting will remain at its original time.",
            "cancel_confirmation": "Alright. Your meeting will remain scheduled as planned."
        }
        return responses.get(action_type, "Thank you for letting me know.")
    
    # Default response
    else:
        return "Thank you for your response. We'll process your request and get back to you."

# =============================================================================
# ORIGINAL ENDPOINTS (Maintained for compatibility)
# =============================================================================

@app.post("/handle-speech")
async def handle_speech(request: Request):
    """Handle speech input from Gather"""
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    call_sid = form_data.get("CallSid", "")
    
    print(f"🎤 Speech from Gather: '{speech_result}'")
    
    if speech_result and len(speech_result.strip()) > 2:
        # Process with LLM and respond immediately
        success = await deliver_immediate_response(speech_result, get_llm_response)
        
        if not success:
            # Fallback response
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <Response>
                <Say voice="alice">I'm sorry, I didn't catch that. Please try again.</Say>
                <Redirect>{BASE_URL}/continue-listening</Redirect>
            </Response>"""
            return Response(content=twiml.strip(), media_type="application/xml")
    
    return Response(content=create_listening_twiml(), media_type="application/xml")

@app.post("/continue-listening")
async def continue_listening(request: Request):
    """Continue listening for more input"""
    logger.info("👂 Continuing to listen...")
    return Response(content=create_listening_twiml(), media_type="application/xml")

@app.websocket("/stream")
async def stream(websocket: WebSocket):
    """WebSocket stream handler - enhanced with context awareness"""
    await websocket.accept()
    logger.info("🔌 Enhanced WebSocket /stream connected")
    
    audio_buffer = bytearray()
    call_sid = None
    consecutive_silent_chunks = 0
    stream_sid = None
    is_processing = False
    total_chunks_received = 0

    SILENCE_THRESHOLD_MS = 2000
    CHUNK_DURATION_MS = 20  
    SILENT_CHUNKS_TO_TRIGGER = SILENCE_THRESHOLD_MS // CHUNK_DURATION_MS
    MIN_AUDIO_LENGTH = 1000

    async def process_and_respond():
        nonlocal audio_buffer, call_sid, consecutive_silent_chunks, is_processing
        
        if not audio_buffer or len(audio_buffer) < 160:
            print(" Audio buffer too small, skipping...")
            return

        if is_processing:
            print(" Already processing, skipping...")
            return

        is_processing = True
        print(f" Processing {len(audio_buffer)} bytes of audio...")
        
        audio_to_process = bytes(audio_buffer)
        audio_buffer.clear()
        consecutive_silent_chunks = 0

        try:
            audio_file = "caller.wav"
            save_ulaw_as_wav(audio_to_process, audio_file)
            
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 1000:
                print(" Audio file too small or doesn't exist")
                is_processing = False
                return
                
            user_text = transcribe_audio(audio_file)
            print(f"Transcribed text: '{user_text}'")

            if user_text and user_text.strip() and len(user_text.strip()) > 2:
                # If we have orchestrator context, handle differently
                if current_call_context:
                    # Send callback to orchestrator
                    await send_callback_to_orchestrator(
                        call_sid=call_sid,
                        status="completed",
                        result="transcription_received",
                        user_response=user_text
                    )
                    
                    # Generate context-aware response
                    action_type = current_call_context.get("action_type", "confirmation")
                    response_text = generate_context_response(user_text, action_type)
                    
                    if call_sid:
                        is_active, status = check_call_status(call_sid)
                        if is_active:
                            success = await speak_via_twiml_say(call_sid, response_text)
                            if success:
                                logger.info("✅ Context-aware response delivered!")
                else:
                    # Use original LLM response
                    success = await deliver_immediate_response(user_text, get_llm_response)
                    
                    if success:
                     print("Response delivered via reliable system!")
                    else:
                     print("Reliable delivery failed, but that's okay")
            else:
                print(f" No meaningful text transcribed: '{user_text}'")
                
        except Exception as e:
            print(f" Error during audio processing: {e}")
            import traceback
            traceback.print_exc()
        finally:
            is_processing = False

    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                audio_chunk = message["bytes"]
                total_chunks_received += 1
                
                if len(audio_chunk) == 0:
                    continue
                
                silence_bytes = sum(1 for byte in audio_chunk if byte in [0xFF, 0x7F, 0x00])
                silence_ratio = silence_bytes / len(audio_chunk)
                is_silent_chunk = silence_ratio > 0.8  
                
                if not is_silent_chunk:
                    consecutive_silent_chunks = 0
                    audio_buffer.extend(audio_chunk)
                else:
                    if len(audio_buffer) > 0:  
                        consecutive_silent_chunks += 1

                if (len(audio_buffer) > MIN_AUDIO_LENGTH * 8 and  
                    consecutive_silent_chunks >= SILENT_CHUNKS_TO_TRIGGER and
                    not is_processing):
                    
                    print(f"🔍 Triggering processing - Buffer: {len(audio_buffer)}, Silent chunks: {consecutive_silent_chunks}")
                    await process_and_respond()

            elif "text" in message:
                try:
                    event_data = json.loads(message["text"])
                    event_type = event_data.get("event")
                    
                    if event_type == "start":
                        start_data = event_data.get("start", {})
                        call_sid = start_data.get("callSid")
                        stream_sid = start_data.get("streamSid")
                        
                        set_current_call_sid(call_sid)
                        
                        logger.info(f"📞 Stream started - CallSid: {call_sid}, StreamSid: {stream_sid}")
                        
                    elif event_type == "media":
                        media_data = event_data.get("media", {})
                        payload = media_data.get("payload", "")
                        
                        if payload:
                            try:
                                audio_data = base64.b64decode(payload)
                                
                                if len(audio_data) > 0:
                                    silence_bytes = sum(1 for byte in audio_data if byte in [0xFF, 0x7F, 0x00])
                                    silence_ratio = silence_bytes / len(audio_data)
                                    is_silent_chunk = silence_ratio > 0.8
                                    
                                    if not is_silent_chunk:
                                        consecutive_silent_chunks = 0
                                        audio_buffer.extend(audio_data)
                                    else:
                                        if len(audio_buffer) > 0:
                                            consecutive_silent_chunks += 1
                                    
                                    if (len(audio_buffer) > MIN_AUDIO_LENGTH * 8 and
                                        consecutive_silent_chunks >= SILENT_CHUNKS_TO_TRIGGER and
                                        not is_processing):
                                        await process_and_respond()
                                        
                            except Exception as e:
                                logger.error(f"❌ Error decoding media payload: {e}")
                                
                    elif event_type == "stop":
                        logger.info("🛑 Stream stopping...")
                        
                        # Send final callback if we have context
                        if current_call_context and call_sid:
                            await send_callback_to_orchestrator(
                                call_sid=call_sid,
                                status="completed",
                                result="call_ended"
                            )
                        
                        if len(audio_buffer) > MIN_AUDIO_LENGTH * 8 and not is_processing:
                            await process_and_respond()
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error parsing JSON message: {e}")

    except Exception as e:
        logger.error(f"❌ Unhandled error in stream: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("🔌 WebSocket connection closed")

# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/play-response")
def play_response():
    """Serve the generated audio response"""
    response_file = "response.wav"
    
    if not os.path.exists(response_file):
        logger.info(f"📁 Audio file {response_file} not found")
        return PlainTextResponse("Audio file not ready", status_code=404)
    
    file_size = os.path.getsize(response_file)
    if file_size < 1000:  
        logger.info(f"📁 Audio file {response_file} is too small ({file_size} bytes)")
        return PlainTextResponse("Audio file is invalid", status_code=404)
    
    logger.info(f"🎵 Serving audio file: {response_file} ({file_size} bytes)")
    return FileResponse(response_file, media_type="audio/wav")

@app.get("/health")
def health_check():
    """Enhanced health check"""
    return {
        "status": "healthy", 
        "message": "Enhanced AI Voice Agent is running",
        "version": "2.0.0",
        "features": ["orchestrator_integration", "context_aware_calls", "callback_support"],
        "current_context": bool(current_call_context)
    }

@app.get("/test-tts")
def test_tts():
    """Test TTS functionality"""
    test_text = "Hello, this is a test of the enhanced text to speech system with orchestrator integration."
    wav_path = text_to_speech(test_text, "test.wav")
    if wav_path:
        return {"status": "success", "wav_file": wav_path, "engine": "Enhanced TTS"}
    return {"status": "failed", "engine": "Enhanced TTS"}

@app.get("/api/v1/status")
def get_system_status():
    """Get current system status and context"""
    return {
        "system": "Enhanced Calling Agent",
        "version": "2.0.0",
        "current_call_context": current_call_context,
        "orchestrator_callback_url": orchestrator_callback_url,
        "integration_features": {
            "custom_call_triggers": True,
            "context_aware_responses": True,
            "orchestrator_callbacks": True,
            "call_control": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )