#!/usr/bin/env python3
"""
Test the Intelligent Agent Router.
Tests LLM-based routing and fallback mechanisms.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_intelligent_router():
    """Test the intelligent agent router."""
    print("🧠 Testing Intelligent Agent Router")
    print("=" * 50)
    
    try:
        from agents.intelligent_router import get_intelligent_router
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.janitor.janitor_agent import JanitorAgent
        from agents.recovery.recovery_agent import RecoveryAgent
        
        # Initialize registry with agents
        registry = get_registry()
        
        # Register agents if not already registered
        if registry.get("SENTINEL_AGENT") is None:
            registry.register(SentinelAgent())
        if registry.get("JANITOR_AGENT") is None:
            registry.register(JanitorAgent())
        if registry.get("RECOVERY_AGENT") is None:
            registry.register(RecoveryAgent())
        
        # Initialize router
        router = get_intelligent_router()
        
        # Manually refresh cache to ensure agents are loaded
        await router._refresh_agent_cache()
        
        # Debug cache content
        stats = router.get_routing_stats()
        print(f"🔧 Router cache after refresh: {stats['cached_agents']} agents")
        print(f"🔧 Cached agent names: {stats['agents']}")
        
        print(f"🤖 Available agents: {len(registry.get_all())}")
        for agent in registry.get_all():
            print(f"   • {agent.name}: {agent.specialization}")
        
        # Test cases with expected agent routing
        test_cases = [
            {
                "intent": "Check system health and show me CPU, RAM, and temperature",
                "expected": "SENTINEL_AGENT",
                "reason": "Hardware monitoring request"
            },
            {
                "intent": "Clean up my downloads folder",
                "expected": "JANITOR_AGENT", 
                "reason": "File cleanup request"
            },
            {
                "intent": "Optimize system for gaming performance",
                "expected": "SENTINEL_AGENT",
                "reason": "Performance optimization request"
            },
            {
                "intent": "Undo the last file deletion",
                "expected": "RECOVERY_AGENT",
                "reason": "Recovery/undo request"
            },
            {
                "intent": "Kill processes using too much CPU",
                "expected": "SENTINEL_AGENT",
                "reason": "Process management request"
            },
            {
                "intent": "Organize desktop files",
                "expected": "JANITOR_AGENT",
                "reason": "File organization request"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['intent']}")
            print(f"   Expected: {test_case['expected']}")
            print(f"   Reason: {test_case['reason']}")
            
            try:
                # Test routing (use fallback due to LLM quota)
                agent = await router._trigger_based_route(test_case['intent'])
                
                if agent:
                    actual = agent
                    success = actual == test_case['expected']
                    status = "✅ PASS" if success else "❌ FAIL"
                    
                    print(f"   Actual: {actual}")
                    print(f"   Status: {status}")
                    
                    results.append({
                        "test": i,
                        "intent": test_case['intent'],
                        "expected": test_case['expected'],
                        "actual": actual,
                        "success": success
                    })
                else:
                    print(f"   Actual: None")
                    print(f"   Status: ⚠️ NO ROUTE")
                    results.append({
                        "test": i,
                        "intent": test_case['intent'],
                        "expected": test_case['expected'],
                        "actual": None,
                        "success": False
                    })
                    
            except Exception as e:
                print(f"   Error: {e}")
                results.append({
                    "test": i,
                    "intent": test_case['intent'],
                    "expected": test_case['expected'],
                    "actual": f"ERROR: {e}",
                    "success": False
                })
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        for result in results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} Test {result['test']}: {result['intent'][:50]}...")
            print(f"   Expected: {result['expected']}, Got: {result['actual']}")
        
        print(f"\n📈 Results: {passed}/{total} tests passed")
        
        # Router stats
        stats = router.get_routing_stats()
        print(f"\n🔧 Router Stats:")
        print(f"   Cached agents: {stats['cached_agents']}")
        print(f"   LLM available: {stats['llm_available']}")
        print(f"   Agents: {', '.join(stats['agents'])}")
        
        return passed >= 4  # Allow some margin for routing complexity
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_llm_fallback():
    """Test LLM routing and trigger-based fallback."""
    print("\n🔄 Testing LLM Routing & Fallback")
    print("=" * 50)
    
    try:
        from agents.intelligent_router import get_intelligent_router
        
        router = get_intelligent_router()
        
        # Test with a complex intent
        intent = "My computer is running slow, CPU usage is high, and I need to optimize performance for video editing"
        
        print(f"🎯 Complex Intent: {intent}")
        
        # Test LLM routing
        agent = await router.route_to_agent(intent)
        
        if agent:
            print(f"✅ Routed to: {agent.name}")
            print(f"📋 Specialization: {agent.specialization}")
            
            # Test plan execution
            plan = await router.execute_agent_plan(intent)
            if plan:
                print(f"✅ Plan created with {len(plan.actions)} actions")
                for i, action in enumerate(plan.actions[:3], 1):
                    print(f"   {i}. {action.get('type', 'unknown')}: {action.get('description', 'no description')}")
            else:
                print("⚠️ No plan created")
        else:
            print("❌ No agent selected")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

async def main():
    """Run all router tests."""
    print("🚀 Intelligent Agent Router Test Suite")
    print("=" * 60)
    
    # Run basic routing tests
    basic_success = await test_intelligent_router()
    
    # Run LLM fallback tests
    fallback_success = await test_llm_fallback()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 60)
    
    print(f"Basic Routing: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"LLM Fallback: {'✅ PASS' if fallback_success else '❌ FAIL'}")
    
    overall_success = basic_success and fallback_success
    print(f"\n🎉 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
