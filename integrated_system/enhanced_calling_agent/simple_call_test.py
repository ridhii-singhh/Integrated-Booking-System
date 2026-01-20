#!/usr/bin/env python3
"""
Simple test to make a direct call using Twilio without webhooks
"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

def make_simple_call():
    """Make a simple call using Twilio"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Create a simple TwiML response
        response = VoiceResponse()
        response.say("Hello! This is a test call from your booking system. The call functionality is working correctly.")
        response.pause(length=1)
        response.say("Thank you for testing the calling feature.")
        
        # Convert TwiML to string
        twiml_string = str(response)
        
        print(f"📞 Making call from {TWILIO_PHONE_NUMBER} to +919193174378")
        print(f"TwiML: {twiml_string}")
        
        # Make the call with TwiML directly
        call = client.calls.create(
            twiml=twiml_string,
            to="+919193174378",
            from_=TWILIO_PHONE_NUMBER,
            timeout=30
        )
        
        print(f"✅ Call initiated successfully!")
        print(f"Call SID: {call.sid}")
        print(f"Status: {call.status}")
        
        return call.sid
        
    except Exception as e:
        print(f"❌ Error making call: {e}")
        return None

if __name__ == "__main__":
    print("🧪 Testing Simple Call Functionality")
    print("=" * 40)
    
    call_sid = make_simple_call()
    if call_sid:
        print(f"✅ Call test completed! SID: {call_sid}")
        print("📞 Check your phone for the call.")
    else:
        print("❌ Call test failed!")
