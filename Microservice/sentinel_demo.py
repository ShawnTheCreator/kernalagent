#!/usr/bin/env python3
"""
Sentinel Agent Demo - Showcasing "God Level" automation capabilities.

This demo demonstrates the Sentinel Agent's ability to transform from a simple
automation tool into a complete PC optimization system - the foundation for
"no hand needs to touch the PC" automation.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def sentinel_demo():
    """Complete Sentinel Agent demonstration."""
    print("🛡️" * 60)
    print("🛡️ SENTINEL AGENT DEMO - 'God Level' PC Automation")
    print("🛡️" * 60)
    print()
    
    try:
        # Initialize Sentinel Agent
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.agent_registry import get_registry
        
        sentinel = SentinelAgent()
        registry = get_registry()
        registry.register(sentinel)
        
        print("🚀 SENTINEL AGENT INITIALIZED")
        print(f"   📋 Name: {sentinel.name}")
        print(f"   🎯 Specialization: {sentinel.specialization}")
        print(f"   🔧 Type: {sentinel.agent_type.value}")
        print(f"   ⚡ Triggers: {len(sentinel.get_triggers())}")
        print()
        
        # ============ PULSE CHECK: Real-time Hardware Monitoring ============
        print("🔍" * 60)
        print("🔍 PULSE CHECK - Real-time Hardware Monitoring")
        print("🔍" * 60)
        
        health_report = await sentinel.get_health_report()
        
        print("📊 SYSTEM HEALTH REPORT:")
        print(f"   💻 CPU Usage: {health_report.get('cpu', {}).get('percent_total', 0)}%")
        print(f"   🧠 RAM Usage: {health_report.get('memory', {}).get('virtual', {}).get('percent_used', 0)}%")
        print(f"   🌡️ Max Temperature: {health_report.get('temperature', {}).get('max_temp', 'N/A')}°C")
        print(f"   ⚙️ Active Processes: {len(health_report.get('processes', []))}")
        print(f"   🚨 Active Alerts: {len(health_report.get('alerts', []))}")
        
        # Show top processes
        processes = health_report.get('processes', [])[:5]
        if processes:
            print("\n🔥 TOP 5 PROCESSES:")
            for i, proc in enumerate(processes, 1):
                print(f"   {i}. {proc['name']} - CPU: {proc['cpu_percent']}%, RAM: {proc['memory_percent']}%")
        
        print()
        
        # ============ CONTEXTUAL GRADING: Intelligent Analysis ============
        print("🧠" * 60)
        print("🧠 CONTEXTUAL GRADING - Intelligent System Analysis")
        print("🧠" * 60)
        
        analysis = await sentinel.analyze({})
        
        print("📈 SYSTEM ANALYSIS RESULTS:")
        print(f"   🎯 Severity: {analysis.severity.upper()}")
        print(f"   💡 Recommendations: {len(analysis.recommendations)}")
        
        if analysis.recommendations:
            print("\n💡 INTELLIGENT RECOMMENDATIONS:")
            for i, rec in enumerate(analysis.recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Show system status
        system_status = analysis.findings.get('system_status', {})
        print(f"\n📊 SYSTEM STATUS OVERVIEW:")
        print(f"   💻 CPU Status: {system_status.get('cpu_status', 'unknown')}")
        print(f"   🧠 Memory Status: {system_status.get('memory_status', 'unknown')}")
        print(f"   🌡️ Thermal Status: {system_status.get('thermal_status', 'unknown')}")
        print(f"   🎯 Overall: {system_status.get('overall_status', 'unknown')}")
        
        print()
        
        # ============ DIAGNOSIS: Resource Hog Identification ============
        print("🔬" * 60)
        print("🔬 DIAGNOSIS - Resource Hog Identification")
        print("🔬" * 60)
        
        resource_hogs = analysis.findings.get('resource_hogs', [])
        if resource_hogs:
            print("🐷 RESOURCE HOGS DETECTED:")
            for i, hog in enumerate(resource_hogs[:3], 1):
                print(f"   {i}. {hog['name']} (PID: {hog['pid']})")
                print(f"      💻 CPU: {hog['cpu_percent']}% | 🧠 RAM: {hog['memory_percent']}%")
                print(f"      📊 Status: {hog['status']}")
        else:
            print("✅ No significant resource hogs detected")
        
        print()
        
        # ============ FOCUS MODE DEMO: Application Optimization ============
        print("🎯" * 60)
        print("🎯 FOCUS MODE - Application Optimization Demo")
        print("🎯" * 60)
        
        # Simulate optimizing for a common application
        target_app = "chrome.exe"
        print(f"🚀 Optimizing system for: {target_app}")
        
        focus_result = await sentinel.optimize_for_focus(target_app)
        
        print("⚡ FOCUS OPTIMIZATION RESULTS:")
        print(f"   ✅ Success: {focus_result.get('success', False)}")
        print(f"   🎯 Target App: {focus_result.get('target_app', 'N/A')}")
        print(f"   ⚙️ Actions Taken: {len(focus_result.get('actions_taken', []))}")
        
        if focus_result.get('actions_taken'):
            print("\n🔧 OPTIMIZATION ACTIONS:")
            for action in focus_result.get('actions_taken', []):
                print(f"   • {action}")
        
        print()
        
        # ============ THERMAL GUARDIAN: Temperature Management ============
        print("🌡️" * 60)
        print("🌡️ THERMAL GUARDIAN - Temperature Management")
        print("🌡️" * 60)
        
        thermal_status = sentinel._thermal_controller.get_current_status()
        
        print("🌡️ THERMAL CONTROLLER STATUS:")
        print(f"   ⚡ Current Power Scheme: {thermal_status.get('current_power_scheme', 'Unknown')}")
        print(f"   🎚️ Temperature Thresholds:")
        
        thresholds = thermal_status.get('temperature_thresholds', {})
        for level, temp in thresholds.items():
            print(f"      {level.capitalize()}: {temp}°C")
        
        # Demonstrate power profile switching
        print(f"\n🔄 Testing power profile management...")
        
        # Try to switch to high performance (will fail gracefully if no admin)
        power_result = await sentinel.set_power_profile("high_performance")
        print(f"   ⚡ High Performance: {'✅' if power_result.get('success') else '⚠️ ' + power_result.get('reason', 'Unknown')}")
        
        # Switch back to balanced
        balanced_result = await sentinel.set_power_profile("balanced")
        print(f"   ⚖️ Balanced: {'✅' if balanced_result.get('success') else '⚠️ ' + balanced_result.get('reason', 'Unknown')}")
        
        print()
        
        # ============ GHOST PROCESS HUNTER: System Cleanup ============
        print("👻" * 60)
        print("👻 GHOST PROCESS HUNTER - System Cleanup")
        print("👻" * 60)
        
        print("🔍 Scanning for ghost processes (idle > 2 hours)...")
        
        ghost_result = await sentinel.cleanup_ghost_processes(idle_hours=2.0)
        
        print("👻 GHOST CLEANUP RESULTS:")
        print(f"   ✅ Success: {ghost_result.get('success', False)}")
        print(f"   🧹 Cleaned: {len(ghost_result.get('processes_cleaned', []))}")
        print(f"   ⏭️ Skipped: {len(ghost_result.get('processes_skipped', []))}")
        
        if ghost_result.get('processes_cleaned'):
            print("\n🧹 CLEANED PROCESSES:")
            for proc in ghost_result.get('processes_cleaned', [])[:3]:
                print(f"   • {proc['name']} (PID: {proc['pid']}) - Age: {proc['age_hours']}h")
        
        print()
        
        # ============ PERFORMANCE METRICS ============
        print("📊" * 60)
        print("📊 SENTINEL PERFORMANCE METRICS")
        print("📊" * 60)
        
        metrics = sentinel.get_metrics()
        
        print("📈 ACCUMULATED METRICS:")
        print(f"   🔍 Health Checks: {metrics.get('health_checks', 0)}")
        print(f"   ⚙️ Optimizations: {metrics.get('optimizations_performed', 0)}")
        print(f"   🗑️ Processes Terminated: {metrics.get('processes_terminated', 0)}")
        print(f"   🌡️ Temperature Alerts: {metrics.get('temperature_alerts', 0)}")
        print(f"   ⚡ Power Profile Changes: {metrics.get('power_profile_changes', 0)}")
        print(f"   👻 Ghost Processes Cleaned: {metrics.get('ghost_processes_cleaned', 0)}")
        
        print()
        
        # ============ AGENT ECOSYSTEM INTEGRATION ============
        print("🤖" * 60)
        print("🤖 AGENT ECOSYSTEM INTEGRATION")
        print("🤖" * 60)
        
        all_agents = registry.get_all()
        print(f"🤖 Total Agents in Ecosystem: {len(all_agents)}")
        
        for agent in all_agents:
            info = agent.get_info()
            print(f"   • {info['name']} - {info['specialization']}")
        
        print()
        
        # ============ CONCLUSION ============
        print("🎉" * 60)
        print("🎉 SENTINEL AGENT DEMO COMPLETE")
        print("🎉" * 60)
        print()
        print("✅ CAPABILITIES DEMONSTRATED:")
        print("   🔍 Real-time hardware monitoring")
        print("   🧠 Intelligent system analysis")
        print("   🎯 Application-specific optimization")
        print("   🌡️ Thermal management")
        print("   👻 Ghost process cleanup")
        print("   ⚡ Power profile management")
        print("   📊 Performance metrics tracking")
        print()
        print("🚀 This transforms Kernal Agent from 'file automation' to")
        print("   'complete PC optimization system' - the foundation for")
        print("   'God Level' automation where no human touch is needed!")
        print()
        print("🛡️ Sentinel Agent: The 'Nervous System' of your PC! 🛡️")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(sentinel_demo())
    sys.exit(0 if success else 1)
