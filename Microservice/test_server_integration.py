#!/usr/bin/env python3
"""
Test Sentinel Agent integration with the main server.
Tests all API endpoints and server functionality.
"""

import asyncio
import sys
import os
import json
import time
import requests
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def log_response(test_name, response, data=None):
    """Log test results."""
    print(f"\n{'='*50}")
    print(f"🧪 {test_name}")
    print(f"📡 Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS")
        if data:
            print(f"📊 Data: {json.dumps(data, indent=2)[:500]}...")
    else:
        print("❌ FAILED")
        print(f"📄 Response: {response.text[:200]}")
    print(f"{'='*50}")

def test_server_health():
    """Test basic server health."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        log_response("Server Health Check", response)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False

def test_agents_list():
    """Test agents list endpoint."""
    try:
        response = requests.get(f"{API_BASE}/agents", timeout=10)
        data = response.json() if response.status_code == 200 else None
        
        log_response("Agents List", response, data)
        
        # Check if Sentinel Agent is in the list
        if data and 'agents' in data:
            sentinel_found = any(agent['name'] == 'SENTINEL_AGENT' for agent in data['agents'])
            print(f"🛡️ Sentinel Agent found: {sentinel_found}")
            
            if sentinel_found:
                sentinel_agent = next(agent for agent in data['agents'] if agent['name'] == 'SENTINEL_AGENT')
                print(f"📋 Specialization: {sentinel_agent['specialization']}")
                print(f"🔧 Type: {sentinel_agent['type']}")
                print(f"⚡ Triggers: {len(sentinel_agent['triggers'])}")
            
            return sentinel_found
        return False
    except Exception as e:
        print(f"❌ Agents list test failed: {e}")
        return False

def test_sentinel_health_report():
    """Test Sentinel health report endpoint."""
    try:
        response = requests.get(f"{API_BASE}/agents/sentinel/health-report", timeout=15)
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Health Report", response, data)
        
        if data:
            # Validate health report structure
            required_keys = ['timestamp', 'system', 'cpu', 'memory', 'temperature', 'processes']
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                print(f"⚠️ Missing keys: {missing_keys}")
            else:
                print("✅ Health report structure valid")
                print(f"💻 CPU Usage: {data.get('cpu', {}).get('percent_total', 0)}%")
                print(f"🧠 RAM Usage: {data.get('memory', {}).get('virtual', {}).get('percent_used', 0)}%")
                print(f"🌡️ Max Temp: {data.get('temperature', {}).get('max_temp', 'N/A')}°C")
                print(f"⚙️ Processes: {len(data.get('processes', []))}")
                print(f"🚨 Alerts: {len(data.get('alerts', []))}")
            
            return len(missing_keys) == 0
        return False
    except Exception as e:
        print(f"❌ Sentinel health report test failed: {e}")
        return False

def test_sentinel_focus_optimization():
    """Test Sentinel focus optimization endpoint."""
    try:
        payload = {"target_app": "chrome.exe"}
        response = requests.post(
            f"{API_BASE}/agents/sentinel/optimize-focus",
            json=payload,
            timeout=10
        )
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Focus Optimization", response, data)
        
        if data:
            print(f"🎯 Target App: {data.get('target_app', 'N/A')}")
            print(f"✅ Success: {data.get('success', False)}")
            print(f"⚙️ Actions: {len(data.get('actions_taken', []))}")
            
            if data.get('actions_taken'):
                for action in data.get('actions_taken', [])[:3]:
                    print(f"   • {action}")
            
            return True
        return False
    except Exception as e:
        print(f"❌ Sentinel focus optimization test failed: {e}")
        return False

def test_sentinel_power_profile():
    """Test Sentinel power profile endpoint."""
    try:
        payload = {"profile": "balanced"}
        response = requests.post(
            f"{API_BASE}/agents/sentinel/power-profile",
            json=payload,
            timeout=10
        )
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Power Profile", response, data)
        
        if data:
            print(f"⚡ Profile: {data.get('profile', 'N/A')}")
            print(f"✅ Success: {data.get('success', False)}")
            print(f"🔄 Previous: {data.get('previous', 'N/A')}")
            
            return data.get('success', False)
        return False
    except Exception as e:
        print(f"❌ Sentinel power profile test failed: {e}")
        return False

def test_sentinel_metrics():
    """Test Sentinel metrics endpoint."""
    try:
        response = requests.get(f"{API_BASE}/agents/sentinel/metrics", timeout=5)
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Metrics", response, data)
        
        if data and 'metrics' in data:
            metrics = data['metrics']
            print("📊 Current Metrics:")
            print(f"   🔍 Health Checks: {metrics.get('health_checks', 0)}")
            print(f"   ⚙️ Optimizations: {metrics.get('optimizations_performed', 0)}")
            print(f"   🗑️ Processes Terminated: {metrics.get('processes_terminated', 0)}")
            print(f"   🌡️ Temperature Alerts: {metrics.get('temperature_alerts', 0)}")
            print(f"   ⚡ Power Profile Changes: {metrics.get('power_profile_changes', 0)}")
            print(f"   👻 Ghost Processes Cleaned: {metrics.get('ghost_processes_cleaned', 0)}")
            
            return True
        return False
    except Exception as e:
        print(f"❌ Sentinel metrics test failed: {e}")
        return False

def test_sentinel_kill_hogs():
    """Test Sentinel kill resource hogs endpoint."""
    try:
        # Use high thresholds to avoid killing important processes
        payload = {"cpu_threshold": 95.0, "ram_threshold": 98.0}
        response = requests.post(
            f"{API_BASE}/agents/sentinel/kill-hogs",
            json=payload,
            timeout=10
        )
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Kill Resource Hogs", response, data)
        
        if data:
            print(f"✅ Success: {data.get('success', False)}")
            print(f"🎯 Processes Targeted: {len(data.get('processes_targeted', []))}")
            print(f"🗑️ Processes Killed: {len(data.get('processes_killed', []))}")
            
            return True
        return False
    except Exception as e:
        print(f"❌ Sentinel kill hogs test failed: {e}")
        return False

def test_sentinel_cleanup_ghosts():
    """Test Sentinel cleanup ghosts endpoint."""
    try:
        # Use high idle threshold to avoid killing active processes
        payload = {"idle_hours": 24.0}
        response = requests.post(
            f"{API_BASE}/agents/sentinel/cleanup-ghosts",
            json=payload,
            timeout=15
        )
        data = response.json() if response.status_code == 200 else None
        
        log_response("Sentinel Cleanup Ghosts", response, data)
        
        if data:
            print(f"✅ Success: {data.get('success', False)}")
            print(f"🧹 Processes Cleaned: {len(data.get('processes_cleaned', []))}")
            print(f"⏭️ Processes Skipped: {len(data.get('processes_skipped', []))}")
            
            return True
        return False
    except Exception as e:
        print(f"❌ Sentinel cleanup ghosts test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Sentinel Agent Server Integration Tests")
    print("=" * 60)
    print(f"🌐 Testing server at: {BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    tests = [
        ("Server Health", test_server_health),
        ("Agents List", test_agents_list),
        ("Sentinel Health Report", test_sentinel_health_report),
        ("Sentinel Focus Optimization", test_sentinel_focus_optimization),
        ("Sentinel Power Profile", test_sentinel_power_profile),
        ("Sentinel Metrics", test_sentinel_metrics),
        ("Sentinel Kill Hogs", test_sentinel_kill_hogs),
        ("Sentinel Cleanup Ghosts", test_sentinel_cleanup_ghosts),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(1)  # Small delay between tests
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Sentinel Agent fully integrated!")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
