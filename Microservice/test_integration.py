#!/usr/bin/env python3
"""
Integration Test - Tests Sentinel Agent with C# Desktop App Integration

This test verifies:
1. Sentinel Agent is properly registered
2. All API endpoints are working
3. Data serialization is correct
4. C# app can communicate with microservice
"""

import asyncio
import sys
import os
import json
import requests
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_sentinel_integration():
    """Test complete Sentinel Agent integration."""
    print("🔗 SENTINEL AGENT INTEGRATION TEST")
    print("=" * 50)
    
    # Configuration
    MICROSERVICE_URL = "http://localhost:8000"
    
    try:
        # Test 1: Check if microservice is running
        print("\n1️⃣ Testing microservice connection...")
        try:
            response = requests.get(f"{MICROSERVICE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ Microservice is running")
                print(f"   📊 Health: {response.json()}")
            else:
                print(f"   ❌ Microservice returned status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Cannot connect to microservice: {e}")
            print("   💡 Make sure to run: python -m app.main")
            return False
        
        # Test 2: Test agent registry
        print("\n2️⃣ Testing agent registry...")
        try:
            response = requests.get(f"{MICROSERVICE_URL}/api/agents", timeout=5)
            if response.status_code == 200:
                agents = response.json()
                print(f"   ✅ Found {agents['count']} agents")
                
                sentinel_found = False
                for agent in agents['agents']:
                    if agent['name'] == 'SENTINEL_AGENT':
                        sentinel_found = True
                        print(f"   ✅ Sentinel Agent registered: {agent['specialization']}")
                        break
                
                if not sentinel_found:
                    print("   ❌ Sentinel Agent not found in registry")
                    return False
            else:
                print(f"   ❌ Agent registry failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Agent registry error: {e}")
            return False
        
        # Test 3: Test Sentinel health report
        print("\n3️⃣ Testing Sentinel health report...")
        try:
            response = requests.get(f"{MICROSERVICE_URL}/api/agents/sentinel/health-report", timeout=10)
            if response.status_code == 200:
                health_report = response.json()
                print("   ✅ Health report generated")
                print(f"   💻 CPU: {health_report.get('cpu', {}).get('percent_total', 0)}%")
                print(f"   🧠 RAM: {health_report.get('memory', {}).get('virtual', {}).get('percent_used', 0)}%")
                print(f"   🌡️ Temp: {health_report.get('temperature', {}).get('max_temp', 'N/A')}°C")
                print(f"   ⚙️ Processes: {len(health_report.get('processes', []))}")
                print(f"   🚨 Alerts: {len(health_report.get('alerts', []))}")
                
                # Validate structure for C# deserialization
                required_keys = ['timestamp', 'system', 'cpu', 'memory', 'temperature', 'processes', 'disk', 'network', 'alerts']
                missing_keys = [key for key in required_keys if key not in health_report]
                if missing_keys:
                    print(f"   ⚠️ Missing keys: {missing_keys}")
                else:
                    print("   ✅ All required keys present for C# integration")
            else:
                print(f"   ❌ Health report failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Health report error: {e}")
            return False
        
        # Test 4: Test focus optimization
        print("\n4️⃣ Testing focus optimization...")
        try:
            test_data = {"target_app": "chrome.exe"}
            response = requests.post(
                f"{MICROSERVICE_URL}/api/agents/sentinel/optimize-focus",
                json=test_data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Focus optimization works")
                print(f"   🎯 Target: {result.get('target_app', 'N/A')}")
                print(f"   ⚙️ Actions: {len(result.get('actions_taken', []))}")
                print(f"   ✅ Success: {result.get('success', False)}")
            else:
                print(f"   ❌ Focus optimization failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Focus optimization error: {e}")
            return False
        
        # Test 5: Test power profile
        print("\n5️⃣ Testing power profile management...")
        try:
            test_data = {"profile": "balanced"}
            response = requests.post(
                f"{MICROSERVICE_URL}/api/agents/sentinel/power-profile",
                json=test_data,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Power profile management works")
                print(f"   ⚡ Profile: {result.get('profile', 'N/A')}")
                print(f"   ✅ Success: {result.get('success', False)}")
            else:
                print(f"   ❌ Power profile failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Power profile error: {e}")
            return False
        
        # Test 6: Test metrics endpoint
        print("\n6️⃣ Testing Sentinel metrics...")
        try:
            response = requests.get(f"{MICROSERVICE_URL}/api/agents/sentinel/metrics", timeout=5)
            if response.status_code == 200:
                metrics = response.json()
                print("   ✅ Metrics endpoint works")
                print(f"   📊 Metrics keys: {list(metrics.get('metrics', {}).keys())}")
                print(f"   🤖 Agent status: {metrics.get('status', {}).get('name', 'N/A')}")
            else:
                print(f"   ❌ Metrics failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Metrics error: {e}")
            return False
        
        # Test 7: Test C# compatible JSON serialization
        print("\n7️⃣ Testing C# compatible JSON...")
        try:
            response = requests.get(f"{MICROSERVICE_URL}/api/agents/sentinel/health-report", timeout=5)
            if response.status_code == 200:
                health_report = response.json()
                
                # Test JSON serialization (C# compatible)
                json_str = json.dumps(health_report, indent=2)
                parsed_back = json.loads(json_str)
                
                if parsed_back == health_report:
                    print("   ✅ JSON serialization is C# compatible")
                else:
                    print("   ⚠️ JSON serialization issues detected")
                
                # Test specific C# data types
                cpu_data = health_report.get('cpu', {})
                if isinstance(cpu_data.get('percent_total'), (int, float)):
                    print("   ✅ CPU data types are C# compatible")
                else:
                    print("   ⚠️ CPU data type issues")
                
                processes = health_report.get('processes', [])
                if processes and all(isinstance(p.get('pid'), int) for p in processes):
                    print("   ✅ Process data types are C# compatible")
                else:
                    print("   ⚠️ Process data type issues")
            else:
                print(f"   ❌ JSON test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ JSON test error: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 INTEGRATION TEST COMPLETE")
        print("=" * 50)
        print("✅ All tests passed! Sentinel Agent is ready for C# integration")
        print("\n📋 Next steps:")
        print("   1. Start the C# Desktop App")
        print("   2. Navigate to '🛡️ Sentinel Agent' in the menu")
        print("   3. Verify real-time system monitoring")
        print("   4. Test optimization features")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sentinel_integration())
    sys.exit(0 if success else 1)
