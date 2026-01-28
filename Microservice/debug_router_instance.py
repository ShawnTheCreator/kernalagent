#!/usr/bin/env python3
"""
Debug the router instance and registry issue.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def debug_router_instance():
    """Debug router instance and registry."""
    print("🔍 Debug Router Instance")
    print("=" * 50)
    
    try:
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.intelligent_router import get_intelligent_router
        
        # Test registry instances
        registry1 = get_registry()
        registry2 = get_registry()
        
        print(f"📋 Registry 1: {id(registry1)}")
        print(f"📋 Registry 2: {id(registry2)}")
        print(f"📋 Same instance: {registry1 is registry2}")
        
        # Register agent
        if registry1.get("SENTINEL_AGENT") is None:
            sentinel = SentinelAgent()
            registry1.register(sentinel)
            print(f"✅ Registered agent in registry1")
        
        # Check both registries
        agents1 = registry1.get_all()
        agents2 = registry2.get_all()
        
        print(f"🤖 Registry1 agents: {len(agents1)}")
        print(f"🤖 Registry2 agents: {len(agents2)}")
        
        # Test router
        router = get_intelligent_router()
        print(f"🧠 Router: {id(router)}")
        print(f"🧠 Router registry: {id(router._registry)}")
        print(f"🧠 Same registry: {router._registry is registry1}")
        
        # Test router cache refresh
        print(f"\n🔄 Testing router cache refresh...")
        
        # Check cache before
        print(f"📊 Cache before: {len(router._agent_cache)} agents")
        
        # Call refresh
        await router._refresh_agent_cache()
        
        # Check cache after
        print(f"📊 Cache after: {len(router._agent_cache)} agents")
        print(f"📊 Cache keys: {list(router._agent_cache.keys())}")
        
        # Test manual registry access from router
        print(f"\n🔧 Testing router registry access...")
        router_agents = router._registry.get_all()
        print(f"🤖 Router registry agents: {len(router_agents)}")
        
        for agent in router_agents:
            print(f"   • {agent.name}")
        
        return len(router._agent_cache) > 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_router_instance())
    print(f"\n🎉 Debug result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
