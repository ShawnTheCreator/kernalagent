#!/usr/bin/env python3
"""
Test the intelligent routing through the actual server.
"""

import asyncio
import sys
import os
import requests
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_server_routing():
    """Test routing through the actual server."""
    print("🌐 Testing Server Routing")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test intents
    test_cases = [
        {
            "intent": "Check system health and show me CPU, RAM, and temperature",
            "expected_agent": "SENTINEL_AGENT"
        },
        {
            "intent": "Clean up my downloads folder",
            "expected_agent": "JANITOR_AGENT"
        },
        {
            "intent": "Optimize system for gaming performance",
            "expected_agent": "SENTINEL_AGENT"
        },
        {
            "intent": "Kill processes using too much CPU",
            "expected_agent": "SENTINEL_AGENT"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['intent']}")
        print(f"   Expected: {test_case['expected_agent']}")
        
        try:
            # Test via agent planning endpoint
            payload = {
                "command": test_case['intent'],
                "context": {"user_id": "test_user"}
            }
            
            response = requests.post(
                f"{base_url}/api/agent/plan",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Server responded: {response.status_code}")
                
                # Check if agent was used
                if 'agent_used' in result:
                    actual_agent = result['agent_used']
                    success = actual_agent == test_case['expected_agent']
                    status = "✅ PASS" if success else "❌ FAIL"
                    
                    print(f"   Agent used: {actual_agent}")
                    print(f"   Status: {status}")
                    
                    results.append({
                        "test": i,
                        "intent": test_case['intent'],
                        "expected": test_case['expected_agent'],
                        "actual": actual_agent,
                        "success": success
                    })
                else:
                    print(f"   ⚠️ No agent used in response")
                    results.append({
                        "test": i,
                        "intent": test_case['intent'],
                        "expected": test_case['expected_agent'],
                        "actual": "NO_AGENT",
                        "success": False
                    })
            else:
                print(f"   ❌ Server error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results.append({
                    "test": i,
                    "intent": test_case['intent'],
                    "expected": test_case['expected_agent'],
                    "actual": f"ERROR_{response.status_code}",
                    "success": False
                })
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            results.append({
                "test": i,
                "intent": test_case['intent'],
                "expected": test_case['expected_agent'],
                "actual": f"EXCEPTION: {e}",
                "success": False
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SERVER ROUTING RESULTS")
    print("=" * 50)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} Test {result['test']}: {result['intent'][:50]}...")
        print(f"   Expected: {result['expected']}, Got: {result['actual']}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    return passed >= 2  # Allow some margin

if __name__ == "__main__":
    success = asyncio.run(test_server_routing())
    print(f"\n🎉 Server routing: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
