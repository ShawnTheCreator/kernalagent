#!/usr/bin/env python3
"""
Simple test script for Sentinel Agent.
Tests hardware monitoring and basic functionality without starting the full server.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_sentinel_agent():
    """Test Sentinel Agent basic functionality."""
    print("🛡️ Testing Sentinel Agent...")
    
    try:
        # Import and initialize Sentinel Agent
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.agent_registry import get_registry
        
        # Create agent instance
        sentinel = SentinelAgent()
        print(f"✅ Sentinel Agent created: {sentinel.name}")
        print(f"📋 Specialization: {sentinel.specialization}")
        print(f"🔧 Agent Type: {sentinel.agent_type.value}")
        
        # Test triggers
        triggers = sentinel.get_triggers()
        print(f"⚡ Triggers defined: {len(triggers)}")
        for trigger in triggers:
            print(f"   - {trigger.trigger_type}: {trigger.condition} (priority: {trigger.priority})")
        
        # Test hardware monitoring
        print("\n🔍 Testing hardware monitoring...")
        health_report = await sentinel.get_health_report()
        
        print(f"📊 Health Report Generated:")
        print(f"   - CPU Usage: {health_report.get('cpu', {}).get('percent_total', 0)}%")
        print(f"   - Memory Usage: {health_report.get('memory', {}).get('virtual', {}).get('percent_used', 0)}%")
        print(f"   - Max Temperature: {health_report.get('temperature', {}).get('max_temp', 'N/A')}°C")
        print(f"   - Process Count: {len(health_report.get('processes', []))}")
        print(f"   - Alerts: {len(health_report.get('alerts', []))}")
        
        # Test analysis
        print("\n🧠 Testing system analysis...")
        analysis = await sentinel.analyze({})
        print(f"📈 Analysis completed:")
        print(f"   - Severity: {analysis.severity}")
        print(f"   - Recommendations: {len(analysis.recommendations)}")
        print(f"   - Findings keys: {list(analysis.findings.keys())}")
        
        if analysis.recommendations:
            print("💡 Recommendations:")
            for rec in analysis.recommendations:
                print(f"   - {rec}")
        
        # Test agent registry
        print("\n📋 Testing agent registry...")
        registry = get_registry()
        registry.register(sentinel)
        
        all_agents = registry.get_all()
        print(f"🤖 Total agents registered: {len(all_agents)}")
        
        sentinel_from_registry = registry.get("SENTINEL_AGENT")
        if sentinel_from_registry:
            print("✅ Sentinel Agent successfully registered and retrieved")
        else:
            print("❌ Sentinel Agent not found in registry")
        
        # Test process optimization (read-only)
        print("\n⚙️ Testing process optimizer...")
        high_resource = await sentinel._hardware_monitor.get_high_resource_processes(cpu_threshold=1.0)
        print(f"🔥 Found {len(high_resource)} high-resource processes")
        
        # Test thermal controller
        print("\n🌡️ Testing thermal controller...")
        thermal_status = sentinel._thermal_controller.get_current_status()
        print(f"📡 Thermal controller status:")
        print(f"   - Current power scheme: {thermal_status.get('current_power_scheme', 'Unknown')}")
        print(f"   - Temperature thresholds: {thermal_status.get('temperature_thresholds', {})}")
        
        print("\n🎉 All Sentinel Agent tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sentinel_agent())
    sys.exit(0 if success else 1)
