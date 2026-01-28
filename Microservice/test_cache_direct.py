#!/usr/bin/env python3
"""
Test cache refresh directly.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_cache_direct():
    """Test cache refresh directly."""
    print("🔍 Test Cache Refresh Direct")
    print("=" * 50)
    
    try:
        # Setup
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        
        registry = get_registry()
        
        if registry.get("SENTINEL_AGENT") is None:
            registry.register(SentinelAgent())
        
        print(f"✅ Registered {len(registry.get_all())} agents")
        
        # Test cache refresh
        from agents.intelligent_router import IntelligentRouter
        
        router = IntelligentRouter()
        
        print(f"🔄 Calling cache refresh directly...")
        await router._refresh_agent_cache()
        
        print(f"📊 Cache result: {len(router._agent_cache)} agents")
        print(f"📊 Cache keys: {list(router._agent_cache.keys())}")
        
        # Test trigger-based routing
        test_intent = "Check system health and show me CPU, RAM, and temperature"
        
        print(f"🎯 Testing routing: {test_intent}")
        result = await router._trigger_based_route(test_intent)
        
        print(f"🤖 Routing result: {result}")
        
        return len(router._agent_cache) > 0 and result == "SENTINEL_AGENT"
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cache_direct())
    print(f"\n🎉 Direct cache test: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
