from twilio.rest import Client
from config import *

def trigger_call(target_phone=None):
    """Trigger an outbound call and return the call SID"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Use target_phone if provided, otherwise use default USER_PHONE_NUMBER
        phone_to_call = target_phone if target_phone else USER_PHONE_NUMBER
        
        print(f" Placing call from {TWILIO_PHONE_NUMBER} to {phone_to_call}")
        
        # Create a simple TwiML response for the call
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.say("Hello! This is a call from your booking system.")
        response.pause(length=1)
        response.say("Your meeting has been scheduled successfully.")
        response.pause(length=1)
        response.say("Please say yes to confirm or no to cancel.")
        response.pause(length=2)
        response.say("Thank you for using our booking system.")
        
        twiml_string = str(response)
        
        # Make the call with TwiML directly (no webhook needed)
        call = client.calls.create(
            twiml=twiml_string,
            to=phone_to_call,
            from_=TWILIO_PHONE_NUMBER,
            timeout=30,  # Ring for 30 seconds
            record=False  
        )
        
        print(f" Call placed successfully!")
        print(f" Call SID: {call.sid}")
        print(f"Status: {call.status}")
        
        return call.sid
        
    except Exception as e:
        error_msg = str(e)
        if "unverified" in error_msg.lower():
            print(f" Error: Phone number is not verified in Twilio trial account.")
            print(f" Please verify the phone number in your Twilio console.")
            print(f" Error details: {error_msg}")
        else:
            print(f" Error placing call: {error_msg}")
        raise e

def get_call_status(call_sid):
    """Check the status of a call"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls(call_sid).fetch()
        return {
            "sid": call.sid,
            "status": call.status,
            "duration": call.duration,
            "from": call.from_,
            "to": call.to
        }
    except Exception as e:
        print(f" Error fetching call status: {e}")
        return None