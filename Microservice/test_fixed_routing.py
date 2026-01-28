#!/usr/bin/env python3
"""
Test fixed routing by ensuring proper initialization order.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_fixed_routing():
    """Test routing with proper initialization."""
    print("🔧 Test Fixed Routing")
    print("=" * 50)
    
    try:
        # Step 1: Import registry and register agents FIRST
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.janitor.janitor_agent import JanitorAgent
        
        registry = get_registry()
        
        # Register agents
        if registry.get("SENTINEL_AGENT") is None:
            registry.register(SentinelAgent())
        if registry.get("JANITOR_AGENT") is None:
            registry.register(JanitorAgent())
        
        print(f"✅ Registered {len(registry.get_all())} agents")
        
        # Step 2: NOW import and create router
        from agents.intelligent_router import get_intelligent_router
        
        router = get_intelligent_router()
        
        # Step 3: Refresh cache with debug
        print(f"🔄 Starting cache refresh...")
        print(f"📊 Registry agents before refresh: {len(registry.get_all())}")
        
        for agent in registry.get_all():
            print(f"   • Agent: {agent.name}")
        
        await router._refresh_agent_cache()
        
        print(f"📊 Cache after refresh: {len(router._agent_cache)} agents")
        print(f"📊 Cache keys: {list(router._agent_cache.keys())}")
        
        # Debug: Check current registry directly
        current_registry = get_registry()
        print(f"🔧 Current registry agents: {len(current_registry.get_all())}")
        for agent in current_registry.get_all():
            print(f"   • Current agent: {agent.name}")
        
        # Step 4: Test routing
        test_intent = "Check system health and show me CPU, RAM, and temperature"
        
        # Use trigger-based routing (avoid LLM quota)
        agent_name = await router._trigger_based_route(test_intent)
        
        print(f"🎯 Intent: {test_intent}")
        print(f"🤖 Routed to: {agent_name}")
        
        # Test full routing
        agent = await router.route_to_agent(test_intent)
        
        if agent:
            print(f"✅ Full routing success: {agent.name}")
            return agent.name == "SENTINEL_AGENT"
        else:
            print("❌ Full routing failed")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixed_routing())
    print(f"\n🎉 Fixed routing: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
