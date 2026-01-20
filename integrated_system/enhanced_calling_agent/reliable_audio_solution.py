import asyncio
import json
import os
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, BASE_URL
from free_tts import text_to_speech

# Global response queue
response_queue = asyncio.Queue()
current_call_sid = None

async def add_response_to_queue(message):
    """Add a response to the queue for playback"""
    await response_queue.put(message)
    print(f" Added to queue: {message[:50]}...")

async def get_next_response():
    """Get the next response from queue (non-blocking)"""
    try:
        return response_queue.get_nowait()
    except asyncio.QueueEmpty:
        return None

def set_current_call_sid(call_sid):
    """Set the current active call SID"""
    global current_call_sid
    current_call_sid = call_sid
    print(f" Set current call SID: {call_sid}")

def get_current_call_sid():
    """Get the current active call SID"""
    return current_call_sid

def create_twiml_with_gather_and_say(message=None):
    """
    Create TwiML that can speak and then gather input continuously
    This keeps the call active and allows for responses
    """
    hostname = BASE_URL.split("://")[1] if "://" in BASE_URL else BASE_URL
    
    # Clean message for XML
    if message:
        clean_message = (message.replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                        .replace("'", '&apos;'))
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>"""
    
    # Add the message if provided
    if message:
        twiml += f"""
        <Say voice="alice">{clean_message}</Say>"""
    
    # Always continue listening
    twiml += f"""
        <Gather input="speech" action="{BASE_URL}/handle-speech" method="POST" speechTimeout="auto" enhanced="true">
            <Say voice="alice">Please continue speaking.</Say>
        </Gather>
        <Redirect>{BASE_URL}/continue-listening</Redirect>
    </Response>"""
    
    return twiml.strip()

def create_listening_twiml():
    """
    Create TwiML that just listens with streaming
    """
    hostname = BASE_URL.split("://")[1] if "://" in BASE_URL else BASE_URL
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Start>
            <Stream url="wss://{hostname}/stream" track="inbound_track" />
        </Start>
        <Gather input="speech" action="{BASE_URL}/handle-speech" method="POST" speechTimeout="auto" enhanced="true">
            <Say voice="alice">I'm listening. Please speak.</Say>
        </Gather>
        <Pause length="30"/>
    </Response>"""
    
    return twiml.strip()

async def deliver_response_safely(message, max_retries=2):
    """
    Safely deliver a response using multiple strategies
    """
    call_sid = get_current_call_sid()
    
    if not call_sid:
        print(" No active call SID")
        return False
    
    if not message or not message.strip():
        print(" No message to deliver")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Strategy 1: Check call status first
        try:
            call = client.calls(call_sid).fetch()
            print(f" Call status: {call.status}")
            
            if call.status not in ['in-progress']:
                print(f" Call not in progress: {call.status}")
                return False
        except Exception as e:
            print(f" Error checking call status: {e}")
            return False
        
        # Strategy 2: Use TwiML with Gather (keeps call active)
        for attempt in range(max_retries):
            try:
                print(f"🔊 Delivering response (attempt {attempt + 1}): {message[:50]}...")
                
                twiml = create_twiml_with_gather_and_say(message)
                
                # Update call with new TwiML
                updated_call = client.calls(call_sid).update(twiml=twiml)
                
                print(f" Response delivered successfully!")
                return True
                
            except Exception as e:
                error_str = str(e).lower()
                print(f" Attempt {attempt + 1} failed: {e}")
                
                if "not in-progress" in error_str or "not found" in error_str:
                    print(" Call ended or not found")
                    return False
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
        
        return False
        
    except Exception as e:
        print(f" Error in deliver_response_safely: {e}")
        return False

# Background task to process queued responses
async def process_response_queue():
    """
    Background task that processes queued responses
    """
    print(" Started response queue processor")
    
    while True:
        try:
            # Check for queued responses
            message = await get_next_response()
            
            if message:
                print(f" Processing queued response: {message[:50]}...")
                success = await deliver_response_safely(message)
                
                if success:
                    print(" Queued response delivered")
                else:
                    print(" Failed to deliver queued response")
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f" Error in response queue processor: {e}")
            await asyncio.sleep(1)

# Start the background task
response_processor_task = None

def start_response_processor():
    """Start the background response processor"""
    global response_processor_task
    if response_processor_task is None or response_processor_task.done():
        response_processor_task = asyncio.create_task(process_response_queue())
        print(" Started response processor task")

def stop_response_processor():
    """Stop the background response processor"""
    global response_processor_task
    if response_processor_task and not response_processor_task.done():
        response_processor_task.cancel()
        print(" Stopped response processor task")

# Simple function to queue responses 
async def queue_ai_response(user_text, llm_response_func):
    """
    Process user input and queue AI response
    """
    try:
        if not user_text or len(user_text.strip()) < 2:
            return False
        
        print(f" Getting LLM response for: {user_text}")
        llm_response = llm_response_func(user_text)
        
        if llm_response and llm_response.strip():
            print(f" LLM Response: {llm_response}")
            await add_response_to_queue(llm_response)
            return True
        else:
            print(" Empty LLM response")
            return False
            
    except Exception as e:
        print(f" Error queuing AI response: {e}")
        return False

async def deliver_immediate_response(user_text, llm_response_func):
    """
    Process and deliver response immediately (bypassing queue)
    """
    try:
        if not user_text or len(user_text.strip()) < 2:
            return False
        
        print(f" Processing immediate response for: {user_text}")
        llm_response = llm_response_func(user_text)
        
        if llm_response and llm_response.strip():
            print(f" Immediate response: {llm_response}")
            return await deliver_response_safely(llm_response)
        else:
            print(" Empty LLM response")
            return False
            
    except Exception as e:
        print(f" Error in immediate response: {e}")
        return False