#!/usr/bin/env python3
"""
Comprehensive test for Sentinel Agent to identify any remaining issues.
Tests all components and edge cases.
"""

import asyncio
import sys
import os
import traceback

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_sentinel_comprehensive():
    """Comprehensive test of all Sentinel Agent functionality."""
    print("🔍 COMPREHENSIVE SENTINEL AGENT TEST")
    print("=" * 50)
    
    issues_found = []
    
    try:
        # Test 1: Import all components
        print("1️⃣ Testing imports...")
        try:
            from agents.sentinel.sentinel_agent import SentinelAgent
            from agents.sentinel.hardware_monitor import HardwareMonitor
            from agents.sentinel.process_optimizer import ProcessOptimizer
            from agents.sentinel.thermal_controller import ThermalController
            print("   ✅ All imports successful")
        except Exception as e:
            issues_found.append(f"Import error: {e}")
            print(f"   ❌ Import failed: {e}")
            return issues_found
        
        # Test 2: Initialize components
        print("\n2️⃣ Testing initialization...")
        try:
            sentinel = SentinelAgent()
            hardware_monitor = HardwareMonitor()
            process_optimizer = ProcessOptimizer()
            thermal_controller = ThermalController()
            print("   ✅ All components initialized")
        except Exception as e:
            issues_found.append(f"Initialization error: {e}")
            print(f"   ❌ Initialization failed: {e}")
            return issues_found
        
        # Test 3: Hardware monitoring
        print("\n3️⃣ Testing hardware monitoring...")
        try:
            health_report = await hardware_monitor.get_health_report()
            
            # Validate health report structure
            required_keys = ['timestamp', 'system', 'cpu', 'memory', 'temperature', 'processes', 'disk', 'network', 'alerts']
            missing_keys = [key for key in required_keys if key not in health_report]
            if missing_keys:
                issues_found.append(f"Health report missing keys: {missing_keys}")
                print(f"   ⚠️ Health report missing: {missing_keys}")
            else:
                print("   ✅ Health report structure valid")
            
            # Test process lookup
            chrome_process = await hardware_monitor.get_process_by_name("chrome.exe")
            print(f"   ✅ Process lookup works (chrome.exe found: {chrome_process is not None})")
            
        except Exception as e:
            issues_found.append(f"Hardware monitoring error: {e}")
            print(f"   ❌ Hardware monitoring failed: {e}")
        
        # Test 4: Process optimizer
        print("\n4️⃣ Testing process optimizer...")
        try:
            # Test high resource process detection
            high_resource = await hardware_monitor.get_high_resource_processes(cpu_threshold=1.0)
            print(f"   ✅ High resource detection found: {len(high_resource)} processes")
            
            # Test focus optimization (read-only)
            if chrome_process:
                focus_result = await process_optimizer.optimize_for_focus("chrome.exe")
                print(f"   ✅ Focus optimization: {focus_result.get('success', False)}")
            
        except Exception as e:
            issues_found.append(f"Process optimizer error: {e}")
            print(f"   ❌ Process optimizer failed: {e}")
        
        # Test 5: Thermal controller
        print("\n5️⃣ Testing thermal controller...")
        try:
            thermal_status = thermal_controller.get_current_status()
            
            # Validate thermal status
            required_keys = ['current_power_scheme', 'temperature_thresholds']
            missing_keys = [key for key in required_keys if key not in thermal_status]
            if missing_keys:
                issues_found.append(f"Thermal status missing keys: {missing_keys}")
                print(f"   ⚠️ Thermal status missing: {missing_keys}")
            else:
                print("   ✅ Thermal status structure valid")
            
            # Test heat source identification
            heat_sources = await thermal_controller.identify_heat_sources(health_report.get('processes', []))
            print(f"   ✅ Heat source identification found: {len(heat_sources)} sources")
            
        except Exception as e:
            issues_found.append(f"Thermal controller error: {e}")
            print(f"   ❌ Thermal controller failed: {e}")
        
        # Test 6: Full agent analysis
        print("\n6️⃣ Testing full agent analysis...")
        try:
            analysis = await sentinel.analyze({})
            
            # Validate analysis structure
            required_keys = ['agent_name', 'findings', 'recommendations', 'severity']
            missing_keys = [key for key in required_keys if key not in analysis.model_dump()]
            if missing_keys:
                issues_found.append(f"Analysis missing keys: {missing_keys}")
                print(f"   ⚠️ Analysis missing: {missing_keys}")
            else:
                print("   ✅ Analysis structure valid")
            
            # Test planning
            plan = await sentinel.plan(analysis)
            print(f"   ✅ Planning created: {len(plan.actions)} actions")
            
        except Exception as e:
            issues_found.append(f"Full analysis error: {e}")
            print(f"   ❌ Full analysis failed: {e}")
        
        # Test 7: Agent registry integration
        print("\n7️⃣ Testing agent registry...")
        try:
            from agents.agent_registry import get_registry
            registry = get_registry()
            registry.register(sentinel)
            
            # Test retrieval
            retrieved = registry.get("SENTINEL_AGENT")
            if retrieved:
                print("   ✅ Agent registry integration works")
            else:
                issues_found.append("Agent registry retrieval failed")
                print("   ❌ Agent registry retrieval failed")
            
        except Exception as e:
            issues_found.append(f"Agent registry error: {e}")
            print(f"   ❌ Agent registry failed: {e}")
        
        # Test 8: Edge cases
        print("\n8️⃣ Testing edge cases...")
        try:
            # Test with invalid process name
            invalid_process = await hardware_monitor.get_process_by_name("definitely_not_real_process.exe")
            if invalid_process is None:
                print("   ✅ Invalid process handling works")
            else:
                issues_found.append("Invalid process should return None")
                print("   ⚠️ Invalid process should return None")
            
            # Test thermal controller with invalid profile
            invalid_profile = await thermal_controller.set_power_profile("invalid_profile")
            if not invalid_profile.get('success', True):
                print("   ✅ Invalid power profile handling works")
            else:
                issues_found.append("Invalid power profile should fail")
                print("   ⚠️ Invalid power profile should fail")
            
        except Exception as e:
            issues_found.append(f"Edge case error: {e}")
            print(f"   ❌ Edge case testing failed: {e}")
        
        # Test 9: Metrics and status
        print("\n9️⃣ Testing metrics and status...")
        try:
            metrics = sentinel.get_metrics()
            status = sentinel.get_status()
            
            if isinstance(metrics, dict) and isinstance(status, dict):
                print("   ✅ Metrics and status retrieval works")
            else:
                issues_found.append("Metrics/status should be dictionaries")
                print("   ❌ Metrics/status should be dictionaries")
            
        except Exception as e:
            issues_found.append(f"Metrics error: {e}")
            print(f"   ❌ Metrics testing failed: {e}")
        
        # Test 10: API endpoint compatibility
        print("\n🔟 Testing API endpoint compatibility...")
        try:
            # Test all public API methods
            health_report = await sentinel.get_health_report()
            focus_result = await sentinel.optimize_for_focus("test.exe")  # Will fail gracefully
            hog_result = await sentinel.kill_resource_hogs(95.0, 98.0)  # High thresholds
            ghost_result = await sentinel.cleanup_ghost_processes(24.0)  # 24 hours
            power_result = await sentinel.set_power_profile("balanced")
            
            print("   ✅ All API methods callable")
            
        except Exception as e:
            issues_found.append(f"API compatibility error: {e}")
            print(f"   ❌ API compatibility failed: {e}")
        
    except Exception as e:
        issues_found.append(f"General test error: {e}")
        print(f"❌ General test failure: {e}")
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 COMPREHENSIVE TEST COMPLETE")
    print("=" * 50)
    
    if issues_found:
        print(f"❌ Issues found: {len(issues_found)}")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        return False
    else:
        print("✅ No issues found - Sentinel Agent is ready!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_sentinel_comprehensive())
    sys.exit(0 if success else 1)
