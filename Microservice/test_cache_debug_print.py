#!/usr/bin/env python3
"""
Test cache with print statements for debugging.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_cache_debug():
    """Test cache with debug prints."""
    print("🔍 Test Cache Debug")
    print("=" * 50)
    
    try:
        # Setup
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        
        registry = get_registry()
        
        if registry.get("SENTINEL_AGENT") is None:
            sentinel = SentinelAgent()
            registry.register(sentinel)
            print(f"✅ Registered {sentinel.name}")
        
        agents = registry.get_all()
        print(f"📋 Registry has {len(agents)} agents")
        
        for agent in agents:
            print(f"   • {agent.name}")
            
            # Test get_info
            try:
                info = agent.get_info()
                print(f"     📋 get_info() works: {type(info)}")
            except Exception as e:
                print(f"     ❌ get_info() failed: {e}")
            
            # Test get_triggers
            try:
                triggers = agent.get_triggers()
                print(f"     ⚡ get_triggers() works: {len(triggers)} triggers")
            except Exception as e:
                print(f"     ❌ get_triggers() failed: {e}")
        
        # Manual cache building
        print(f"\n🔧 Manual cache test...")
        cache = {}
        
        for agent in agents:
            print(f"🔄 Processing {agent.name}...")
            
            try:
                info = agent.get_info()
                print(f"   📋 Info type: {type(info)}")
                
                # Convert to dict
                if hasattr(info, 'model_dump'):
                    agent_dict = info.model_dump()
                    print(f"   📋 Used model_dump()")
                elif isinstance(info, dict):
                    agent_dict = info.copy()
                    print(f"   📋 Used copy()")
                else:
                    agent_dict = str(info)
                    print(f"   📋 Used str()")
                
                triggers = agent.get_triggers()
                agent_dict['triggers'] = triggers
                
                cache[agent.name] = agent_dict
                print(f"   ✅ Cached {agent.name}")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📊 Manual cache result: {len(cache)} agents")
        for name in cache.keys():
            print(f"   • {name}")
        
        return len(cache) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cache_debug())
    print(f"\n🎉 Debug test: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
