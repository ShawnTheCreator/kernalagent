"""
Quick Import Test - Verify Enhanced System Integration

This script performs a rapid verification that all enhanced components
can be imported and initialized without conflicts.
"""

import sys
import os
import traceback
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_core_imports():
    """Test core system imports first."""
    print("🔍 Testing core system imports...")
    
    try:
        # Existing core components
        from app.agents.base_agent import BaseAgent, AgentType
        from app.agents.agent_registry import get_registry
        from app.core.config import settings
        print("✅ Core components imported successfully")
        
        # Main app (this is critical)
        from app.main import app
        print("✅ Main FastAPI app imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Core imports failed: {e}")
        traceback.print_exc()
        return False

def test_enhanced_agent_imports():
    """Test enhanced agent imports."""
    print("\n🤖 Testing enhanced agent imports...")
    
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.janitor.janitor_tools import FileAnalyzer, safe_move
        print("✅ JanitorAgent and tools imported")
        
        from app.agents.productivity.productivity_agent import ProductivityAgent
        print("✅ ProductivityAgent imported")
        
        from app.agents.security.security_agent import SecurityAgent
        print("✅ SecurityAgent imported")
        
        return True
    except Exception as e:
        print(f"❌ Enhanced agent imports failed: {e}")
        traceback.print_exc()
        return False

def test_enhanced_system_imports():
    """Test enhanced system component imports."""
    print("\n⚙️ Testing enhanced system component imports...")
    
    try:
        from app.automation.scheduler import SmartScheduler, get_scheduler
        print("✅ Scheduler system imported")
        
        from app.notifications.notification_manager import get_notification_manager
        print("✅ Notification system imported")
        
        from app.voice.enhanced_voice_control import get_voice_control
        print("✅ Voice control system imported")
        
        from app.reasoning.llm_planner import WorkflowEngine
        print("✅ Enhanced workflow engine imported")
        
        return True
    except Exception as e:
        print(f"❌ Enhanced system imports failed: {e}")
        traceback.print_exc()
        return False

def test_agent_instantiation():
    """Test that agents can be created."""
    print("\n🚀 Testing agent instantiation...")
    
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        
        # Create instances
        janitor = JanitorAgent()
        productivity = ProductivityAgent()
        security = SecurityAgent()
        
        # Verify basic properties
        assert janitor.name == "JANITOR_AGENT"
        assert productivity.name == "PRODUCTIVITY_AGENT"
        assert security.name == "SECURITY_AGENT"
        
        print(f"✅ Created {janitor.name}")
        print(f"✅ Created {productivity.name}")
        print(f"✅ Created {security.name}")
        
        return True
    except Exception as e:
        print(f"❌ Agent instantiation failed: {e}")
        traceback.print_exc()
        return False

def test_registry_integration():
    """Test registry integration."""
    print("\n📋 Testing registry integration...")
    
    try:
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        registry = get_registry()
        original_count = len(registry.get_all())
        
        # Test registration
        test_agent = JanitorAgent()
        registry.register(test_agent)
        
        new_count = len(registry.get_all())
        assert new_count == original_count + 1
        
        # Test retrieval
        retrieved = registry.get("JANITOR_AGENT")
        assert retrieved is not None
        assert retrieved.name == "JANITOR_AGENT"
        
        print(f"✅ Registry integration successful - {new_count} agents registered")
        return True
        
    except Exception as e:
        print(f"❌ Registry integration failed: {e}")
        traceback.print_exc()
        return False

def test_startup_simulation():
    """Test startup event simulation."""
    print("\n🚀 Testing startup event simulation...")
    
    try:
        # Simulate the startup registration process
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        from app.voice.enhanced_voice_control import get_voice_control
        from app.notifications.notification_manager import get_notification_manager
        
        # Clear registry for clean test
        registry = get_registry()
        registry._agents = {}
        registry._by_type = {agent_type: [] for agent_type in registry._by_type}
        
        # Register agents like startup event
        agents = [JanitorAgent(), ProductivityAgent(), SecurityAgent()]
        for agent in agents:
            registry.register(agent)
        
        # Initialize enhanced systems
        voice_control = get_voice_control()
        notification_manager = get_notification_manager()
        
        print(f"✅ Startup simulation successful - {len(registry.get_all())} agents registered")
        print("✅ Enhanced systems initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Startup simulation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run quick import verification."""
    print("🔬 Quick Import Test - Enhanced System Verification")
    print("=" * 65)
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    
    tests = [
        ("Core Imports", test_core_imports),
        ("Enhanced Agent Imports", test_enhanced_agent_imports),
        ("Enhanced System Imports", test_enhanced_system_imports),
        ("Agent Instantiation", test_agent_instantiation),
        ("Registry Integration", test_registry_integration),
        ("Startup Simulation", test_startup_simulation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        start_time = datetime.now()
        
        try:
            if test_func():
                passed += 1
                duration = (datetime.now() - start_time).total_seconds()
                print(f"✅ {test_name} PASSED ({duration:.2f}s)")
            else:
                failed += 1
                duration = (datetime.now() - start_time).total_seconds()
                print(f"❌ {test_name} FAILED ({duration:.2f}s)")
        except Exception as e:
            failed += 1
            duration = (datetime.now() - start_time).total_seconds()
            print(f"💥 {test_name} CRASHED ({duration:.2f}s): {e}")
    
    # Summary
    print("\n" + "=" * 65)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 65)
    print(f"Total Tests: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed + failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 QUICK TEST PASSED!")
        print("✅ All enhanced components import successfully")
        print("✅ No import conflicts detected") 
        print("✅ System ready for deeper testing")
        
        print("\n📋 VERIFIED ENHANCEMENTS:")
        print("   • JanitorAgent - File management automation")
        print("   • ProductivityAgent - Workflow automation")
        print("   • SecurityAgent - Security monitoring")
        print("   • SmartScheduler - Intelligent task scheduling")
        print("   • NotificationManager - Multi-channel alerts")
        print("   • EnhancedVoiceControl - Advanced voice features")
        print("   • WorkflowEngine - Conditional logic support")
        
        return True
    else:
        print(f"\n⚠️ {failed} QUICK TESTS FAILED!")
        print("❗ Import/integration issues detected")
        print("🔧 Please resolve before running deeper tests")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n⏰ Completed: {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Quick test crashed: {e}")
        traceback.print_exc()
        sys.exit(1)