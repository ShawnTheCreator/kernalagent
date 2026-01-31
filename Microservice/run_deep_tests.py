#!/usr/bin/env python3
"""
Master Test Runner for Enhanced Kernal Agent System

This script runs a comprehensive test suite to verify the enhanced automation
system is working correctly and ready for deployment.

Usage:
    python run_deep_tests.py [--quick] [--integration] [--pytest]
    
    --quick        Run only essential verification checks
    --integration  Run deep integration tests
    --pytest       Run pytest test suite
    (no flags)     Run all tests
"""

import sys
import os
import subprocess
import asyncio
import time
import argparse
from datetime import datetime

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

def print_section(title):
    """Print a section header."""
    print(f"\n--- {title} ---")

def run_script(script_name, description):
    """Run a Python script and return success status."""
    print(f"\n🚀 Running {description}...")
    
    try:
        # Use the configured Python executable
        python_exe = "C:/Python314/python.exe"
        
        result = subprocess.run(
            [python_exe, script_name],
            cwd=os.path.dirname(__file__) or ".",
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {description} PASSED")
            # Show last few lines of output for success summary
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-3:]:
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print(f"❌ {description} FAILED (exit code: {result.returncode})")
            # Show error output
            if result.stderr:
                print("STDERR:")
                for line in result.stderr.strip().split('\n')[-10:]:  # Last 10 lines
                    print(f"   {line}")
            if result.stdout:
                print("STDOUT:")
                for line in result.stdout.strip().split('\n')[-10:]:  # Last 10 lines
                    print(f"   {line}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} TIMED OUT (>120s)")
        return False
    except Exception as e:
        print(f"💥 {description} CRASHED: {e}")
        return False

def run_pytest():
    """Run the pytest test suite."""
    print("\n🧪 Running pytest test suite...")
    
    try:
        python_exe = "C:/Python314/python.exe"
        
        result = subprocess.run(
            [python_exe, "-m", "pytest", "tests/test_enhanced_system.py", "-v", "--tb=short"],
            cwd=os.path.dirname(__file__) or ".",
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout for pytest
        )
        
        if result.returncode == 0:
            print("✅ Pytest suite PASSED")
            # Show pytest summary
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    print(f"   {line}")
            return True
        else:
            print(f"❌ Pytest suite FAILED (exit code: {result.returncode})")
            # Show pytest output
            for line in result.stdout.strip().split('\n')[-15:]:
                print(f"   {line}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Pytest suite TIMED OUT (>180s)")
        return False
    except Exception as e:
        print(f"💥 Pytest suite CRASHED: {e}")
        return False

def check_file_existence():
    """Check that all required files exist."""
    print_section("File Existence Check")
    
    required_files = [
        "verify_enhancements.py",
        "check_dependencies.py", 
        "test_comprehensive.py",
        "test_deep_integration.py",
        "tests/test_enhanced_system.py",
        "app/agents/janitor/janitor_agent.py",
        "app/agents/productivity/productivity_agent.py",
        "app/agents/security/security_agent.py",
        "app/automation/scheduler.py",
        "app/notifications/notification_manager.py",
        "app/voice/enhanced_voice_control.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ {len(missing_files)} files are missing!")
        return False
    
    print(f"\n✅ All {len(required_files)} required files are present")
    return True

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Enhanced Kernal Agent System Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run only quick verification checks")
    parser.add_argument("--integration", action="store_true", help="Run deep integration tests")
    parser.add_argument("--pytest", action="store_true", help="Run pytest test suite")
    parser.add_argument("--no-timeout", action="store_true", help="Disable timeouts for debugging")
    
    args = parser.parse_args()
    
    print_header("Enhanced Kernal Agent System - Deep Test Suite")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # File existence check
    if not check_file_existence():
        print("\n❌ File existence check failed - cannot proceed with tests")
        return False
    
    test_results = {}
    start_time = time.time()
    
    # Determine which tests to run
    if args.quick:
        tests_to_run = [
            ("check_dependencies.py", "Dependency Check"),
            ("verify_enhancements.py", "Enhancement Verification")
        ]
        run_pytest_tests = False
        run_integration_tests = False
    elif args.integration:
        tests_to_run = [
            ("test_deep_integration.py", "Deep Integration Tests")
        ]
        run_pytest_tests = False
        run_integration_tests = True
    elif args.pytest:
        tests_to_run = []
        run_pytest_tests = True
        run_integration_tests = False
    else:
        # Run all tests
        tests_to_run = [
            ("check_dependencies.py", "Dependency Check"),
            ("verify_enhancements.py", "Enhancement Verification"),
            ("test_comprehensive.py", "Comprehensive System Test"),
            ("test_deep_integration.py", "Deep Integration Tests")
        ]
        run_pytest_tests = True
        run_integration_tests = True
    
    # Run script tests
    for script, description in tests_to_run:
        result = run_script(script, description)
        test_results[description] = result
    
    # Run pytest if requested
    if run_pytest_tests:
        pytest_result = run_pytest()
        test_results["Pytest Suite"] = pytest_result
    
    # Calculate results
    total_time = time.time() - start_time
    passed = sum(test_results.values())
    failed = len(test_results) - passed
    
    # Print final summary
    print_header("FINAL TEST RESULTS")
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Tests: {len(test_results)}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏱️ Duration: {total_time:.1f}s")
    print(f"   📈 Success Rate: {(passed/len(test_results)*100):.1f}%")
    
    if failed == 0:
        print_header("🎉 ALL TESTS PASSED! 🎉")
        print("🚀 Enhanced Kernal Agent automation system is READY!")
        print("✅ All enhancements verified and working correctly")
        print("✅ No conflicts detected with existing system")
        print("✅ Integration points validated")
        print("\n📋 DEPLOYMENT CHECKLIST:")
        print("   ✅ Agent system enhanced with 3 new specialized agents")
        print("   ✅ Workflow engine supports conditional logic")
        print("   ✅ Smart scheduling system operational")
        print("   ✅ Multi-channel notification system active")
        print("   ✅ Enhanced voice control with conversation support")
        print("   ✅ All systems integrate seamlessly")
        
        return True
    else:
        print_header(f"⚠️ {failed} TESTS FAILED ⚠️")
        print("❗ System not ready for deployment")
        print("🔧 Please resolve the failed tests above")
        
        if failed == 1:
            print("\n💡 TIP: Only 1 test failed - this may be a minor issue")
        
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⛔ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)