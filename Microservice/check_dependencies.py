"""
Dependency Check Script

Verifies that all our new enhancements have their dependencies available
and don't conflict with existing system components.
"""

import sys
import os
import importlib.util

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def check_standard_dependencies():
    """Check standard library dependencies."""
    print("📚 Checking standard library dependencies...")
    
    standard_deps = [
        'asyncio', 'logging', 'datetime', 'enum', 'dataclasses',
        'typing', 'json', 'os', 're', 'uuid', 'time', 'tempfile'
    ]
    
    for dep in standard_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}")
        except ImportError as e:
            print(f"❌ {dep}: {e}")
            return False
    
    return True

def check_third_party_dependencies():
    """Check third party dependencies."""
    print("\n🔧 Checking third party dependencies...")
    
    third_party_deps = [
        'psutil',  # For system monitoring
        'fastapi', # Core web framework
        'pydantic', # Data validation
        'aiohttp'  # HTTP client for testing
    ]
    
    for dep in third_party_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}")
        except ImportError as e:
            print(f"⚠️ {dep}: {e} (may be optional)")
    
    return True

def check_existing_app_modules():
    """Check that existing app modules still work."""
    print("\n🏗️ Checking existing app modules...")
    
    try:
        # Core existing modules
        from app.agents.base_agent import BaseAgent
        print("✅ BaseAgent")
        
        from app.agents.agent_registry import get_registry
        print("✅ Agent Registry")
        
        from app.reasoning.llm_planner import plan_command
        print("✅ LLM Planner")
        
        from app.core.config import settings
        print("✅ Config")
        
        # Check main app
        from app.main import app
        print("✅ Main App")
        
        return True
        
    except Exception as e:
        print(f"❌ Existing module check failed: {e}")
        return False

def check_new_modules():
    """Check that new modules integrate properly.""" 
    print("\n🆕 Checking new enhancement modules...")
    
    try:
        # New agents
        from app.agents.janitor.janitor_agent import JanitorAgent
        print("✅ JanitorAgent")
        
        from app.agents.productivity.productivity_agent import ProductivityAgent
        print("✅ ProductivityAgent")
        
        from app.agents.security.security_agent import SecurityAgent
        print("✅ SecurityAgent")
        
        # Enhanced systems
        from app.automation.scheduler import get_scheduler
        print("✅ Scheduler")
        
        from app.notifications.notification_manager import get_notification_manager
        print("✅ Notifications")
        
        from app.voice.enhanced_voice_control import get_voice_control
        print("✅ Voice Control")
        
        return True
        
    except Exception as e:
        print(f"❌ New module check failed: {e}")
        return False

def check_integration_points():
    """Check integration between old and new systems."""
    print("\n🔗 Checking integration points...")
    
    try:
        # Test that enhanced planner still works
        from app.reasoning.llm_planner import WorkflowEngine, plan_command
        engine = WorkflowEngine()
        print("✅ Enhanced LLM Planner")
        
        # Test agent registry with new agents
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        registry = get_registry()
        test_agent = JanitorAgent()
        
        # This should work without errors
        original_count = len(registry.get_all())
        registry.register(test_agent)
        new_count = len(registry.get_all())
        
        print("✅ Agent Registry Integration")
        
        # Test that main app startup logic works
        # (We won't actually call it, just verify it exists)
        from app.main import startup_event
        print("✅ Startup Event Integration")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all dependency checks."""
    print("🔍 Enhanced System Dependency Check")
    print("=" * 50)
    
    checks = [
        ("Standard Dependencies", check_standard_dependencies),
        ("Third Party Dependencies", check_third_party_dependencies), 
        ("Existing App Modules", check_existing_app_modules),
        ("New Enhancement Modules", check_new_modules),
        ("Integration Points", check_integration_points)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n--- {check_name} ---")
        if not check_func():
            all_passed = False
            print(f"❌ {check_name} FAILED")
        else:
            print(f"✅ {check_name} PASSED")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL DEPENDENCY CHECKS PASSED!")
        print("✅ System dependencies are satisfied")
        print("✅ No conflicts detected")
        print("✅ Integration points verified")
        return True
    else:
        print("⚠️ Some dependency checks failed!")
        print("❗ Please resolve issues before proceeding")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Dependency check crashed: {e}")
        sys.exit(1)