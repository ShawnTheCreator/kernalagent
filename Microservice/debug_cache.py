#!/usr/bin/env python3
"""
Debug the agent cache issue step by step.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def debug_cache():
    """Debug the cache issue."""
    print("🔍 Debug Agent Cache Issue")
    print("=" * 50)
    
    try:
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        
        # Test registry
        registry = get_registry()
        print(f"📋 Registry type: {type(registry)}")
        
        # Register agent
        if registry.get("SENTINEL_AGENT") is None:
            sentinel = SentinelAgent()
            registry.register(sentinel)
            print(f"✅ Registered SENTINEL_AGENT: {sentinel.name}")
        
        # Get agents
        agents = registry.get_all()
        print(f"🤖 Agents in registry: {len(agents)}")
        
        for agent in agents:
            print(f"   • {agent.name} (type: {type(agent)})")
            
            # Test get_info
            try:
                info = agent.get_info()
                print(f"     📋 Info type: {type(info)}")
                print(f"     📋 Info: {info}")
            except Exception as e:
                print(f"     ❌ get_info failed: {e}")
            
            # Test get_triggers
            try:
                triggers = agent.get_triggers()
                print(f"     ⚡ Triggers: {len(triggers)}")
                for trigger in triggers:
                    print(f"       - {trigger.trigger_type}: {trigger.condition}")
            except Exception as e:
                print(f"     ❌ get_triggers failed: {e}")
        
        # Test manual cache building
        print(f"\n🔧 Testing manual cache building...")
        cache = {}
        
        for agent in agents:
            try:
                agent_info = agent.get_info()
                print(f"📋 Raw agent_info for {agent.name}: {type(agent_info)}")
                
                # Convert to dict
                if hasattr(agent_info, 'model_dump'):
                    agent_dict = agent_info.model_dump()
                elif hasattr(agent_info, 'dict'):
                    agent_dict = agent_info.dict()
                elif isinstance(agent_info, dict):
                    agent_dict = agent_info.copy()
                else:
                    agent_dict = str(agent_info)
                
                print(f"📋 Converted agent_dict type: {type(agent_dict)}")
                
                # Add triggers
                triggers = agent.get_triggers()
                agent_dict['triggers'] = triggers
                
                cache[agent.name] = agent_dict
                print(f"✅ Cached {agent.name}")
                
            except Exception as e:
                print(f"❌ Failed to cache {agent.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📊 Cache result: {len(cache)} agents")
        for name, data in cache.items():
            print(f"   • {name}: {len(data.get('triggers', []))} triggers")
        
        return len(cache) > 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_cache())
    print(f"\n🎉 Debug result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
