import os
import asyncio
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, BASE_URL

def create_play_and_continue_twiml(audio_url, stream_url):
    """
    Create TwiML that plays audio and then continues listening
    """
    hostname = BASE_URL.split("://")[1] if "://" in BASE_URL else BASE_URL
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Play>{audio_url}</Play>
        <Start>
            <Stream url="wss://{hostname}/stream" track="inbound_track" />
        </Start>
        <Pause length="60"/>
    </Response>"""
    
    return twiml.strip()

async def play_audio_via_twiml_update(call_sid, audio_file_path, max_retries=3):
    """
    Play audio by updating the call with new TwiML.
    This approach is more reliable than streaming through WebSocket.
    """
    if not call_sid:
        print(" No call_sid provided")
        return False
    
    if not os.path.exists(audio_file_path):
        print(f" Audio file not found: {audio_file_path}")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # check if the call is still active
        call = client.calls(call_sid).fetch()
        print(f" Call status: {call.status}")
        
        if call.status not in ['in-progress', 'ringing']:
            print(f" Call is not active (status: {call.status})")
            return False
        
        # Create the audio URL
        audio_url = f"{BASE_URL}/play-response"
        stream_url = f"wss://{BASE_URL.split('://')[1]}/stream"
        
        # Create TwiML to play audio and continue streaming
        twiml = create_play_and_continue_twiml(audio_url, stream_url)
        
        # Try to update the call with retries
        for attempt in range(max_retries):
            try:
                print(f" Updating call (attempt {attempt + 1})...")
                
                # Update the call
                updated_call = client.calls(call_sid).update(twiml=twiml)
                
                print(f" Call updated successfully: {updated_call.status}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f" Attempt {attempt + 1} failed: {error_msg}")
                
                if "not in-progress" in error_msg.lower():
                    print(" Call ended, cannot play audio")
                    return False
                
                if attempt < max_retries - 1:
                    print(f" Waiting before retry...")
                    await asyncio.sleep(1)
                else:
                    print(" All retry attempts failed")
                    return False
        
        return False
        
    except Exception as e:
        print(f" Error in play_audio_via_twiml_update: {e}")
        return False

def create_simple_twiml_response(message):
    """
    Create a simple TwiML response with Say and continue streaming
    """
    hostname = BASE_URL.split("://")[1] if "://" in BASE_URL else BASE_URL
    
    # Clean the message for TTS
    clean_message = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="alice">{clean_message}</Say>
        <Start>
            <Stream url="wss://{hostname}/stream" track="inbound_track" />
        </Start>
        <Pause length="60"/>
    </Response>"""
    
    return twiml.strip()

async def speak_via_twiml_say(call_sid, message, max_retries=3):
    """
    Use Twilio's built-in TTS via <Say> verb instead of custom TTS.
    This is more reliable and doesn't require file hosting.
    """
    if not call_sid:
        print(" No call_sid provided")
        return False
    
    if not message or not message.strip():
        print(" No message to speak")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Check call status
        call = client.calls(call_sid).fetch()
        print(f" Call status: {call.status}")
        
        if call.status not in ['in-progress', 'ringing']:
            print(f" Call is not active (status: {call.status})")
            return False
        
        # Create TwiML with Say verb
        twiml = create_simple_twiml_response(message)
        
        # Try to update the call
        for attempt in range(max_retries):
            try:
                print(f" Speaking message (attempt {attempt + 1}): {message[:50]}...")
                
                updated_call = client.calls(call_sid).update(twiml=twiml)
                
                print(f" Message sent successfully: {updated_call.status}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f" Attempt {attempt + 1} failed: {error_msg}")
                
                if "not in-progress" in error_msg.lower():
                    print(" Call ended, cannot speak")
                    return False
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    print(" All retry attempts failed")
        
        return False
        
    except Exception as e:
        print(f" Error in speak_via_twiml_say: {e}")
        return False

def check_call_status(call_sid):
    """
    Check if a call is still active and can be updated
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls(call_sid).fetch()
        
        active_statuses = ['in-progress', 'ringing']
        is_active = call.status in active_statuses
        
        print(f" Call {call_sid}: {call.status} (Active: {is_active})")
        return is_active, call.status
        
    except Exception as e:
        print(f" Error checking call status: {e}")
        return False, "error"

# Alternative: Queue-based response system
class ResponseQueue:
    def __init__(self):
        self.responses = []
        self.is_playing = False
    
    def add_response(self, message):
        """Add a response to the queue"""
        self.responses.append(message)
        print(f" Added to queue: {message[:50]}... (Queue size: {len(self.responses)})")
    
    def get_next_response(self):
        """Get the next response from the queue"""
        if self.responses:
            return self.responses.pop(0)
        return None
    
    def has_responses(self):
        """Check if there are pending responses"""
        return len(self.responses) > 0

response_queue = ResponseQueue()

async def queue_response_for_playback(message):
    """
    Add a response to the queue for playback
    """
    response_queue.add_response(message)
    return True

def get_queued_response():
    """
    Get the next queued response
    """
    return response_queue.get_next_response()

def has_queued_responses():
    """
    Check if there are queued responses
    """
    return response_queue.has_responses()

# Test functions
async def test_twiml_update():
    """Test the TwiML update functionality"""
    print("🧪 Testing TwiML update...")
    
    test_message = "This is a test message from the AI assistant."
    test_call_sid = "TEST_CALL_SID"  
    
    result = await speak_via_twiml_say(test_call_sid, test_message)
    print(f"Say verb test: {'✅ Success' if result else '❌ Failed'}")
    
    is_active, status = check_call_status(test_call_sid)
    print(f"Call status test: {status} (Active: {is_active})")

if __name__ == "__main__":
    asyncio.run(test_twiml_update())