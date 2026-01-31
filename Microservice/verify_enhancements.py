#!/usr/bin/env python3
"""
Quick Verification Script for Enhanced Kernal Agent System

This script performs essential verification checks that can be run safely
without starting the full microservice. It validates the core enhancements.
"""

import sys
import os
import traceback

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def verify_imports():
    """Verify all enhanced modules can be imported."""
    print("🔍 Verifying module imports...")
    
    try:
        # Core agent imports
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        print("✅ All agent modules imported successfully")
        
        # Enhanced systems
        from app.automation.scheduler import SmartScheduler, get_scheduler
        from app.notifications.notification_manager import get_notification_manager
        from app.voice.enhanced_voice_control import get_voice_control
        from app.reasoning.llm_planner import WorkflowEngine
        print("✅ All enhanced system modules imported successfully")
        
        # Agent registry
        from app.agents.agent_registry import get_registry
        print("✅ Agent registry imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import verification failed: {e}")
        traceback.print_exc()
        return False

def verify_agent_creation():
    """Verify agents can be created and have required methods."""
    print("\n🤖 Verifying agent creation...")
    
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        
        agents = [JanitorAgent(), ProductivityAgent(), SecurityAgent()]
        
        for agent in agents:
            assert hasattr(agent, 'name'), f"{agent.__class__.__name__} missing name"
            assert hasattr(agent, 'agent_type'), f"{agent.__class__.__name__} missing agent_type"
            assert hasattr(agent, 'analyze'), f"{agent.__class__.__name__} missing analyze method"
            assert hasattr(agent, 'plan'), f"{agent.__class__.__name__} missing plan method"
            assert hasattr(agent, 'execute'), f"{agent.__class__.__name__} missing execute method"
            assert hasattr(agent, 'get_triggers'), f"{agent.__class__.__name__} missing get_triggers method"
            
            print(f"✅ {agent.name} created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Agent creation verification failed: {e}")
        traceback.print_exc()
        return False

def verify_registry():
    """Verify agent registry functionality."""
    print("\n📋 Verifying agent registry...")
    
    try:
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        
        registry = get_registry()
        
        # Clear and register agents
        registry._agents = {}
        registry._by_type = {agent_type: [] for agent_type in registry._by_type}
        
        agents = [JanitorAgent(), ProductivityAgent(), SecurityAgent()]
        for agent in agents:
            registry.register(agent)
        
        assert len(registry.get_all()) == 3, "Registry should have 3 agents"
        assert registry.get("JANITOR_AGENT") is not None, "JanitorAgent not found in registry"
        assert registry.get("PRODUCTIVITY_AGENT") is not None, "ProductivityAgent not found in registry"
        assert registry.get("SECURITY_AGENT") is not None, "SecurityAgent not found in registry"
        
        # Test intent matching
        matches = registry.find_by_intent("clean up files")
        assert len(matches) > 0, "No agents matched cleanup intent"
        
        print(f"✅ Registry verified - {len(registry.get_all())} agents registered")
        return True
        
    except Exception as e:
        print(f"❌ Registry verification failed: {e}")
        traceback.print_exc()
        return False

def verify_enhanced_systems():
    """Verify enhanced systems can be initialized."""
    print("\n⚙️ Verifying enhanced systems...")
    
    try:
        # Scheduler
        from app.automation.scheduler import get_scheduler, SmartScheduler
        scheduler = get_scheduler()
        assert isinstance(scheduler, SmartScheduler), "Scheduler not properly initialized"
        print("✅ Scheduler system verified")
        
        # Notification manager
        from app.notifications.notification_manager import get_notification_manager
        notification_manager = get_notification_manager()
        assert notification_manager is not None, "Notification manager not initialized"
        assert hasattr(notification_manager, 'templates'), "Notification manager missing templates"
        print("✅ Notification system verified")
        
        # Voice control
        from app.voice.enhanced_voice_control import get_voice_control
        voice_control = get_voice_control()
        assert voice_control is not None, "Voice control not initialized"
        assert hasattr(voice_control, 'intent_patterns'), "Voice control missing intent patterns"
        print("✅ Voice control system verified")
        
        # Workflow engine
        from app.reasoning.llm_planner import WorkflowEngine
        workflow_engine = WorkflowEngine()
        assert workflow_engine is not None, "Workflow engine not initialized"
        print("✅ Workflow engine verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced systems verification failed: {e}")
        traceback.print_exc()
        return False

def verify_file_structure():
    """Verify that all required files exist."""
    print("\n📁 Verifying file structure...")
    
    required_files = [
        "app/agents/janitor/janitor_agent.py",
        "app/agents/janitor/janitor_tools.py",
        "app/agents/productivity/productivity_agent.py",
        "app/agents/security/security_agent.py",
        "app/automation/scheduler.py",
        "app/notifications/notification_manager.py",
        "app/voice/enhanced_voice_control.py",
        "app/reasoning/llm_planner.py",
        "app/agents/agent_registry.py",
        "app/main.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def main():
    """Run all verification checks."""
    print("🔬 Enhanced Kernal Agent System Verification")
    print("=" * 60)
    
    checks = [
        ("File Structure", verify_file_structure),
        ("Module Imports", verify_imports),
        ("Agent Creation", verify_agent_creation),
        ("Agent Registry", verify_registry),
        ("Enhanced Systems", verify_enhanced_systems)
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        print(f"\n--- {check_name} ---")
        try:
            if check_func():
                passed += 1
                print(f"✅ {check_name} PASSED")
            else:
                failed += 1
                print(f"❌ {check_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 {check_name} CRASHED: {e}")
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total Checks: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("🚀 Enhanced automation system is ready!")
        
        # Show summary of enhancements
        print("\n📈 ENHANCEMENT SUMMARY:")
        print("   • JanitorAgent - Autonomous file management")
        print("   • ProductivityAgent - Meeting/task automation") 
        print("   • SecurityAgent - Threat detection & remediation")
        print("   • Smart Scheduler - Cron & event-driven automation")
        print("   • Notification System - Multi-channel delivery")
        print("   • Enhanced Voice Control - Multi-turn conversations")
        print("   • Workflow Engine - Conditional logic support")
        
        return True
    else:
        print(f"\n⚠️ {failed} verifications failed!")
        print("❗ Please fix the issues before proceeding.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⛔ Verification interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Verification crashed: {e}")
        traceback.print_exc()
        sys.exit(1)