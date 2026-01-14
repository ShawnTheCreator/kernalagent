"""
Automation Integration Test

Tests all automation endpoints and Gemini reasoning layer.
Run with: python test_automation.py
"""

import asyncio
import httpx
import json

BASE_URL = "https://kernalagent.onrender.com"

# Test cases for different command types
TEST_COMMANDS = [
    # App Control
    {"command": "open notepad", "expected_action": "open_app"},
    {"command": "open chrome", "expected_action": "open_app"},
    {"command": "close notepad", "expected_action": "close_app"},
    
    # Volume
    {"command": "volume up", "expected_action": "volume_up"},
    {"command": "mute", "expected_action": "volume_mute"},
    
    # Window
    {"command": "minimize", "expected_action": "minimize_window"},
    {"command": "maximize", "expected_action": "maximize_window"},
    
    # System
    {"command": "screenshot", "expected_action": "screenshot"},
    {"command": "lock screen", "expected_action": "lock_screen"},
    
    # Search
    {"command": "search for cats", "expected_action": "open_app"},
    
    # Type
    {"command": "type hello world", "expected_action": "type_text"},
    
    # Typo tolerance
    {"command": "open notpad", "expected_action": "open_app"},  # typo
    {"command": "open crome", "expected_action": "open_app"},   # typo
]


async def test_health():
    """Test health endpoint."""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"ERROR: {e}")
            return False


async def test_agent_health():
    """Test agent health endpoint."""
    print("\n" + "="*60)
    print("TEST: Agent Health (Gemini Status)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(f"{BASE_URL}/api/agent/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"ERROR: {e}")
            return False


async def test_plan_endpoint(command: str, expected_action: str):
    """Test plan endpoint with a command."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/agent/plan",
                json={"command": command}
            )
            
            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            steps = data.get("steps", [])
            
            if not steps:
                print(f"  ❌ No steps returned")
                return False
            
            first_action = steps[0].get("action", "")
            
            if first_action == expected_action:
                print(f"  ✅ '{command}' → {first_action}")
                return True
            else:
                print(f"  ⚠️  '{command}' → {first_action} (expected {expected_action})")
                return False
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            return False


async def test_all_commands():
    """Test all command types."""
    print("\n" + "="*60)
    print("TEST: Plan Endpoint - All Commands")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test in TEST_COMMANDS:
        result = await test_plan_endpoint(test["command"], test["expected_action"])
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


async def test_gemini_endpoint():
    """Test Gemini-only endpoint."""
    print("\n" + "="*60)
    print("TEST: Gemini Plan Endpoint")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/agent/plan/gemini",
                json={"command": "open notepad and type hello"}
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Steps: {len(data.get('steps', []))}")
                for step in data.get("steps", []):
                    print(f"  - {step.get('action')}: {step.get('target') or step.get('content') or ''}")
                return True
            elif response.status_code == 503:
                print("Gemini not available (expected if not deployed)")
                return True
            else:
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: {e}")
            return False


async def main():
    """Run all tests."""
    print("="*60)
    print("AUTOMATION INTEGRATION TEST")
    print(f"Target: {BASE_URL}")
    print("="*60)
    
    results = []
    
    # Test 1: Health
    results.append(await test_health())
    
    # Test 2: Agent Health
    results.append(await test_agent_health())
    
    # Test 3: All commands
    results.append(await test_all_commands())
    
    # Test 4: Gemini endpoint
    results.append(await test_gemini_endpoint())
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = all(results)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
