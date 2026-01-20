#!/usr/bin/env python3
"""
Test script to verify calling functionality
"""
import requests
import json
import time

def test_calling_agent_health():
    """Test if calling agent is running"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        print(f"✅ Calling Agent Health: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Calling Agent Health Check Failed: {e}")
        return False

def test_trigger_call():
    """Test triggering a call"""
    try:
        data = {
            "target_phone": "+919193174378",
            "call_script": "Hello, this is a test call from the booking system. Please say yes to confirm.",
            "context": {
                "action_type": "test",
                "transaction_id": "test_123"
            },
            "action_type": "test"
        }
        
        print("📞 Testing call trigger...")
        print(f"Data: {json.dumps(data, indent=2)}")
        
        response = requests.post(
            "http://localhost:8001/api/v1/trigger-call",
            json=data,
            timeout=30
        )
        
        print(f"✅ Call Trigger Response: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
        
    except Exception as e:
        print(f"❌ Call Trigger Failed: {e}")
        return None

def test_twilio_config():
    """Test Twilio configuration"""
    try:
        from twilio.rest import Client
        from enhanced_calling_agent.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
        
        print("🔧 Testing Twilio Configuration...")
        print(f"Account SID: {TWILIO_ACCOUNT_SID[:10]}...")
        print(f"Phone Number: {TWILIO_PHONE_NUMBER}")
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Test account info
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"✅ Twilio Account Status: {account.status}")
        print(f"Account Name: {account.friendly_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Twilio Configuration Failed: {e}")
        return False

def main():
    print("🧪 Testing Calling Functionality")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_calling_agent_health():
        print("❌ Calling agent is not running. Please start it first.")
        return
    
    # Test 2: Twilio config
    if not test_twilio_config():
        print("❌ Twilio configuration is invalid.")
        return
    
    # Test 3: Trigger call
    result = test_trigger_call()
    if result and result.get("success"):
        print("✅ Call trigger test successful!")
        print("📞 Check your phone for the call.")
    else:
        print("❌ Call trigger test failed!")

if __name__ == "__main__":
    main()
