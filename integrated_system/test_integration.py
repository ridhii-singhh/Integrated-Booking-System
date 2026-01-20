#!/usr/bin/env python3
"""
Integration test script for the Integrated Booking & Calling System
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8080"
BOOKING_AGENT_URL = "http://localhost:8000"
CALLING_AGENT_URL = "http://localhost:8001"

class IntegrationTester:
    """Integration test suite"""
    
    def __init__(self):
        self.session = None
        self.results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_service_health(self, service_name: str, url: str, endpoint: str = "/health"):
        """Test service health"""
        print(f"🏥 Testing {service_name} health...")
        
        try:
            async with self.session.get(f"{url}{endpoint}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ {service_name}: {data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"  ❌ {service_name}: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ {service_name}: {str(e)}")
            return False
    
    async def test_booking_agent_direct(self):
        """Test Booking Agent directly"""
        print("\n📅 Testing Booking Agent directly...")
        
        test_command = "book a test meeting with test@example.com tomorrow at 2 PM for 1 hour"
        
        try:
            data = {"command": test_command}
            async with self.session.post(f"{BOOKING_AGENT_URL}/api/v1/book", json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ Booking Agent: {result.get('message', 'Success')}")
                    return True
                else:
                    print(f"  ❌ Booking Agent: {result.get('detail', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ Booking Agent: {str(e)}")
            return False
    
    async def test_calling_agent_direct(self):
        """Test Calling Agent directly"""
        print("\n📞 Testing Enhanced Calling Agent...")
        
        # Test health endpoint
        health_ok = await self.test_service_health("Enhanced Calling Agent", CALLING_AGENT_URL)
        
        if not health_ok:
            return False
        
        # Test system status endpoint
        try:
            async with self.session.get(f"{CALLING_AGENT_URL}/api/v1/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"  ✅ Calling Agent Status: {status.get('system')}")
                    print(f"     Features: {', '.join(status.get('integration_features', {}).keys())}")
                    return True
                else:
                    print(f"  ❌ Calling Agent Status: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Calling Agent Status: {str(e)}")
            return False
    
    async def test_orchestrator_health(self):
        """Test Orchestrator health"""
        print("\n🔧 Testing Orchestrator health...")
        
        try:
            async with self.session.get(f"{ORCHESTRATOR_URL}/api/v1/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"  ✅ Orchestrator: {health.get('orchestrator', 'unknown')}")
                    
                    # Check dependent services
                    services = health.get('services', {})
                    for service, status in services.items():
                        status_icon = "✅" if "healthy" in status else "❌"
                        print(f"     {status_icon} {service}: {status}")
                    
                    return True
                else:
                    print(f"  ❌ Orchestrator: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Orchestrator: {str(e)}")
            return False
    
    async def test_web_ui(self):
        """Test Web UI accessibility"""
        print("\n🌐 Testing Web UI...")
        
        try:
            async with self.session.get(f"{ORCHESTRATOR_URL}/") as response:
                if response.status == 200:
                    content = await response.text()
                    if "Integrated Booking & Calling System" in content:
                        print("  ✅ Web UI: Accessible and contains expected content")
                        return True
                    else:
                        print("  ❌ Web UI: Missing expected content")
                        return False
                else:
                    print(f"  ❌ Web UI: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Web UI: {str(e)}")
            return False
    
    async def test_integrated_booking_dry_run(self):
        """Test integrated booking (dry run - no actual call)"""
        print("\n🎯 Testing Integrated Booking (dry run)...")
        
        test_data = {
            "booking_command": "book a test integration meeting with test@example.com tomorrow at 3 PM for 30 minutes",
            "trigger_call": False,  # Dry run - no actual call
            "user_phone": "+1234567890",
            "call_delay_minutes": 0
        }
        
        try:
            async with self.session.post(f"{ORCHESTRATOR_URL}/api/v1/integrated-booking", json=test_data) as response:
                result = await response.json()
                
                if response.status == 200:
                    print(f"  ✅ Integrated Booking: {result.get('message', 'Success')}")
                    transaction_id = result.get('transaction_id')
                    
                    if transaction_id:
                        print(f"     Transaction ID: {transaction_id}")
                        
                        # Test transaction status
                        await asyncio.sleep(1)  # Give it a moment
                        await self.test_transaction_status(transaction_id)
                    
                    return True
                else:
                    print(f"  ❌ Integrated Booking: {result.get('detail', 'Unknown error')}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ Integrated Booking: {str(e)}")
            return False
    
    async def test_transaction_status(self, transaction_id: str):
        """Test transaction status retrieval"""
        print(f"\n📊 Testing Transaction Status for {transaction_id[:8]}...")
        
        try:
            async with self.session.get(f"{ORCHESTRATOR_URL}/api/v1/transaction/{transaction_id}") as response:
                if response.status == 200:
                    transaction = await response.json()
                    print(f"  ✅ Transaction Status: {transaction.get('state', 'unknown')}")
                    print(f"     Action Type: {transaction.get('action_type', 'unknown')}")
                    print(f"     Created: {transaction.get('created_at', 'unknown')}")
                    return True
                else:
                    print(f"  ❌ Transaction Status: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Transaction Status: {str(e)}")
            return False
    
    async def test_transactions_list(self):
        """Test transactions list"""
        print("\n📋 Testing Transactions List...")
        
        try:
            async with self.session.get(f"{ORCHESTRATOR_URL}/api/v1/transactions?limit=5") as response:
                if response.status == 200:
                    transactions = await response.json()
                    print(f"  ✅ Transactions List: {len(transactions)} transactions")
                    
                    for tx in transactions[:3]:  # Show first 3
                        print(f"     - {tx.get('action_type', 'unknown')} [{tx.get('state', 'unknown')}]")
                    
                    return True
                else:
                    print(f"  ❌ Transactions List: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Transactions List: {str(e)}")
            return False
    
    async def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test auth stats (should be accessible without auth)
        try:
            async with self.session.get(f"{ORCHESTRATOR_URL}/auth/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    print(f"  ✅ Auth Stats: {stats.get('active_sessions', 0)} active sessions")
                    print(f"     Google Auth Enabled: {stats.get('google_auth_enabled', False)}")
                    return True
                else:
                    print(f"  ❌ Auth Stats: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"  ❌ Auth Stats: {str(e)}")
            return False
    
    async def run_full_test_suite(self):
        """Run complete integration test suite"""
        print("🚀 Starting Integration Test Suite")
        print("=" * 60)
        
        tests = [
            ("Service Health Checks", self.test_services_health),
            ("Orchestrator Health", self.test_orchestrator_health),
            ("Web UI", self.test_web_ui),
            ("Booking Agent Direct", self.test_booking_agent_direct),
            ("Calling Agent Direct", self.test_calling_agent_direct),
            ("Integrated Booking", self.test_integrated_booking_dry_run),
            ("Transactions List", self.test_transactions_list),
            ("Authentication", self.test_auth_endpoints)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            start_time = time.time()
            
            try:
                success = await test_func()
                duration = time.time() - start_time
                results.append((test_name, success, duration))
                
                if success:
                    print(f"✅ {test_name} PASSED ({duration:.2f}s)")
                else:
                    print(f"❌ {test_name} FAILED ({duration:.2f}s)")
                    
            except Exception as e:
                duration = time.time() - start_time
                results.append((test_name, False, duration))
                print(f"💥 {test_name} CRASHED: {str(e)} ({duration:.2f}s)")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for _, success, _ in results if success)
        failed_tests = total_tests - passed_tests
        total_time = sum(duration for _, _, duration in results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        
        print("\nDetailed Results:")
        for test_name, success, duration in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name} ({duration:.2f}s)")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! System is ready for use.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please check the services and configuration.")
        
        return failed_tests == 0
    
    async def test_services_health(self):
        """Test all service health checks"""
        services = [
            ("Orchestrator", ORCHESTRATOR_URL, "/api/v1/health"),
            ("Booking Agent", BOOKING_AGENT_URL, "/api/v1/health"),
            ("Calling Agent", CALLING_AGENT_URL, "/health")
        ]
        
        all_healthy = True
        for name, url, endpoint in services:
            healthy = await self.test_service_health(name, url, endpoint)
            all_healthy = all_healthy and healthy
        
        return all_healthy

async def main():
    """Main test runner"""
    print("🧪 Integrated Booking & Calling System - Integration Tests")
    print("=" * 60)
    print("This script will test all components of the integrated system.")
    print("Make sure all services are running before starting the tests.")
    print("")
    
    # Check if user wants to continue
    try:
        input("Press Enter to start the tests (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\nTests cancelled by user.")
        return
    
    async with IntegrationTester() as tester:
        success = await tester.run_full_test_suite()
        
        if success:
            print("\n🎯 Next Steps:")
            print("1. Open http://localhost:8080 in your browser")
            print("2. Configure your Google and Twilio credentials in .env")
            print("3. Test the booking and calling features")
            return 0
        else:
            print("\n🔧 Troubleshooting:")
            print("1. Ensure all services are running:")
            print("   - Booking Agent: http://localhost:8000")
            print("   - Calling Agent: http://localhost:8001")
            print("   - Orchestrator: http://localhost:8080")
            print("2. Check the service logs for error messages")
            print("3. Verify your .env configuration")
            return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)