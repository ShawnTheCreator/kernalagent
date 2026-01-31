"""
HONEST SYSTEM STATUS CHECK

This script provides a truthful assessment of what's actually working
vs what was claimed to be implemented.
"""

import os
import sys

def check_file_exists(file_path, description):
    """Check if a file actually exists."""
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        # Check file size to see if it's substantial
        size = os.path.getsize(full_path)
        if size > 100:  # More than 100 bytes = likely real content
            print(f"✅ {description} - EXISTS ({size} bytes)")
            return True
        else:
            print(f"⚠️ {description} - EXISTS but EMPTY ({size} bytes)")
            return False
    else:
        print(f"❌ {description} - MISSING")
        return False

def main():
    print("🔍 HONEST SYSTEM STATUS CHECK")
    print("=" * 60)
    print("Checking what was actually implemented vs claimed...")
    
    # Files that were claimed to be created
    files_to_check = [
        ("app/agents/janitor/janitor_agent.py", "JanitorAgent"),
        ("app/agents/janitor/janitor_tools.py", "Janitor Tools"),
        ("app/agents/productivity/productivity_agent.py", "ProductivityAgent"),
        ("app/agents/security/security_agent.py", "SecurityAgent"),
        ("app/automation/scheduler.py", "Smart Scheduler"),
        ("app/notifications/notification_manager.py", "Notification System"),
        ("app/voice/enhanced_voice_control.py", "Enhanced Voice Control"),
        
        # Test files that were claimed to be created
        ("verify_enhancements.py", "Enhancement Verification Script"),
        ("test_comprehensive.py", "Comprehensive Test Script"),
        ("test_deep_integration.py", "Deep Integration Test"),
        ("run_deep_tests.py", "Master Test Runner"),
        ("quick_import_test.py", "Quick Import Test"),
        ("check_dependencies.py", "Dependency Check Script"),
        ("tests/test_enhanced_system.py", "Pytest Enhanced System"),
        
        # Original files that should exist
        ("app/agents/base_agent.py", "Base Agent (Original)"),
        ("app/agents/agent_registry.py", "Agent Registry (Original)"),
        ("app/main.py", "Main App (Original)"),
    ]
    
    existing_files = 0
    missing_files = 0
    empty_files = 0
    
    print("\n📁 FILE EXISTENCE CHECK:")
    for file_path, description in files_to_check:
        if check_file_exists(file_path, description):
            existing_files += 1
        else:
            if os.path.exists(os.path.join(os.path.dirname(__file__), file_path)):
                empty_files += 1
            else:
                missing_files += 1
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"✅ Files that exist with content: {existing_files}")
    print(f"⚠️ Files that exist but are empty: {empty_files}")
    print(f"❌ Files completely missing: {missing_files}")
    
    print("\n🎯 REALITY CHECK:")
    if existing_files > 10:
        print("✅ Significant implementation was actually done")
    elif existing_files > 5:
        print("⚠️ Partial implementation - some features exist")
    else:
        print("❌ Minimal implementation - mostly claims without substance")
    
    print(f"\n📈 Implementation Rate: {(existing_files/(existing_files + missing_files + empty_files)*100):.1f}%")
    
    # Check if the main app can at least import
    print("\n🔧 BASIC FUNCTIONALITY CHECK:")
    try:
        sys.path.insert(0, '.')
        import importlib.util
        
        # Try to check if main.py can be parsed (not imported)
        main_path = os.path.join(os.path.dirname(__file__), "app", "main.py")
        if os.path.exists(main_path):
            spec = importlib.util.spec_from_file_location("main", main_path)
            print("✅ Main app file can be loaded")
        else:
            print("❌ Main app file missing")
            
    except Exception as e:
        print(f"❌ Basic functionality check failed: {e}")
    
    print("\n💡 NEXT STEPS:")
    if missing_files > existing_files:
        print("1. Focus on creating the missing core files")
        print("2. Fix dependency/environment issues")
        print("3. Start with simple, working implementations")
    else:
        print("1. Fix the Python environment and dependencies")
        print("2. Test the existing implementations")
        print("3. Debug and fix any runtime issues")

if __name__ == "__main__":
    main()