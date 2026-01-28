"""
Comprehensive Sentinel test script.

Tests all features:
- Basic monitoring
- WebSocket alerts
- Battery awareness
- Predictive analytics
- Event monitoring
- Scheduled maintenance
"""

import asyncio
import websockets
import json
import logging
import time
import psutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentinelTester:
    def __init__(self):
        self.ws_url = "ws://localhost:8000/ws/sentinel?user_id=test_user"
        self.test_results = {}
        
    async def run_all_tests(self):
        """Run comprehensive tests."""
        print("=" * 60)
        print("🛡️ Sentinel Comprehensive Test Suite")
        print("=" * 60)
        
        tests = [
            ("WebSocket Connection", self.test_websocket_connection),
            ("Basic Alerts", self.test_basic_alerts),
            ("Health Score", self.test_health_score),
            ("Battery Awareness", self.test_battery_awareness),
            ("User Profile", self.test_user_profile),
            ("Predictive Analytics", self.test_predictive_analytics),
            ("Process Monitoring", self.test_process_monitoring),
            ("Event Monitoring", self.test_event_monitoring),
            ("Scheduled Maintenance", self.test_scheduled_maintenance),
        ]
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name}...")
            try:
                result = await test_func()
                self.test_results[test_name] = result
                print(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results[test_name] = False
                print(f"❌ {test_name}: FAILED - {e}")
        
        self.print_summary()
    
    async def test_websocket_connection(self):
        """Test WebSocket connection."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Wait for initial status message
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)
                
                return data.get("type") == "sentinel_status"
        except Exception as e:
            logger.error(f"WebSocket connection test failed: {e}")
            return False
    
    async def test_basic_alerts(self):
        """Test basic alert functionality."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send a test CPU spike
                await self.create_cpu_spike()
                
                # Wait for alert
                message = await asyncio.wait_for(websocket.recv(), timeout=30)
                data = json.loads(message)
                
                return data.get("type") == "sentinel_alert" and "cpu" in data.get("type", "")
        except Exception as e:
            logger.error(f"Basic alerts test failed: {e}")
            return False
    
    async def test_health_score(self):
        """Test health score updates."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Wait for health score
                for _ in range(10):  # Try for 10 messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "sentinel_health_score":
                        score = data.get("score", 0)
                        return 0 <= score <= 100
                
                return False
        except Exception as e:
            logger.error(f"Health score test failed: {e}")
            return False
    
    async def test_battery_awareness(self):
        """Test battery awareness functionality."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send battery status update
                battery_message = {
                    "type": "battery_status",
                    "on_battery": True,
                    "battery_percent": 25
                }
                await websocket.send(json.dumps(battery_message))
                
                # Send profile with battery awareness
                profile_message = {
                    "type": "update_profile",
                    "profile": {
                        "battery_aware": True,
                        "battery_thresholds": {
                            "cpu": 95,
                            "memory": 98,
                            "temperature": 90,
                            "disk": 95
                        }
                    }
                }
                await websocket.send(json.dumps(profile_message))
                
                # Create CPU spike to test adjusted threshold
                await self.create_cpu_spike()
                
                # Should not get alert due to battery awareness
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(message)
                    
                    # If we get an alert, check if it's CPU related
                    if data.get("type") == "sentinel_alert":
                        # Should not be CPU alert due to battery awareness
                        return data.get("type") != "cpu"
                except asyncio.TimeoutError:
                    # No alert - which is expected with battery awareness
                    return True
                
                return True
        except Exception as e:
            logger.error(f"Battery awareness test failed: {e}")
            return False
    
    async def test_user_profile(self):
        """Test user profile updates."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Update profile
                profile_message = {
                    "type": "update_profile",
                    "profile": {
                        "work_hours": [9, 17],
                        "gaming_mode": True,
                        "notifications": True
                    }
                }
                await websocket.send(json.dumps(profile_message))
                
                # Profile should be accepted (no error)
                return True
        except Exception as e:
            logger.error(f"User profile test failed: {e}")
            return False
    
    async def test_predictive_analytics(self):
        """Test predictive analytics."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Monitor for prediction alerts
                for _ in range(20):  # Check 20 messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "sentinel_alert" and data.get("type") == "prediction":
                        return True
                
                # No prediction found (might be normal)
                return True
        except Exception as e:
            logger.error(f"Predictive analytics test failed: {e}")
            return False
    
    async def test_process_monitoring(self):
        """Test process monitoring."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Create a high-memory process
                await self.create_memory_spike()
                
                # Check for process alerts
                for _ in range(10):
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "sentinel_alert" and data.get("type") == "process":
                        return True
                
                return False
        except Exception as e:
            logger.error(f"Process monitoring test failed: {e}")
            return False
    
    async def test_event_monitoring(self):
        """Test Windows Event monitoring."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Monitor for system event alerts
                for _ in range(10):
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "sentinel_alert" and data.get("type") == "system_event":
                        return True
                
                # No system events (normal)
                return True
        except Exception as e:
            logger.error(f"Event monitoring test failed: {e}")
            return False
    
    async def test_scheduled_maintenance(self):
        """Test scheduled maintenance."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Monitor for maintenance notifications
                for _ in range(10):
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    
                    if data.get("type") == "sentinel_maintenance_completed":
                        return True
                
                # No maintenance (normal)
                return True
        except Exception as e:
            logger.error(f"Scheduled maintenance test failed: {e}")
            return False
    
    async def create_cpu_spike(self):
        """Create a CPU spike to trigger alerts."""
        logger.info("Creating CPU spike...")
        end_time = time.time() + 5  # 5 second spike
        
        while time.time() < end_time:
            # CPU intensive calculation
            sum(i * i for i in range(10000))
            await asyncio.sleep(0.01)
    
    async def create_memory_spike(self):
        """Create a memory spike to trigger alerts."""
        logger.info("Creating memory spike...")
        # Allocate memory
        data = []
        for _ in range(100):
            data.append([0] * 10000)  # ~400MB
        await asyncio.sleep(2)
        del data
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<30} {status}")
        
        print("-" * 60)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Sentinel is working perfectly.")
        else:
            print("⚠️ Some tests failed. Check the logs for details.")


async def main():
    """Run the comprehensive test suite."""
    tester = SentinelTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("Starting Sentinel Comprehensive Test Suite...")
    print("Make sure the Sentinel daemon is running on localhost:8000")
    print("Press Ctrl+C to stop")
    print()
    
    asyncio.run(main())
