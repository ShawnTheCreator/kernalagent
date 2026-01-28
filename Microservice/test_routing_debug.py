#!/usr/bin/env python3
"""
Debug test for agent routing to understand why it's not working.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def debug_routing():
    """Debug the routing logic step by step."""
    print("🔍 Debug Agent Routing")
    print("=" * 50)
    
    try:
        from agents.agent_registry import get_registry
        from agents.sentinel.sentinel_agent import SentinelAgent
        from agents.janitor.janitor_agent import JanitorAgent
        
        # Initialize registry
        registry = get_registry()
        
        # Register agents
        if registry.get("SENTINEL_AGENT") is None:
            registry.register(SentinelAgent())
        if registry.get("JANITOR_AGENT") is None:
            registry.register(JanitorAgent())
        
        print(f"🤖 Registered agents: {len(registry.get_all())}")
        
        # Test intent
        intent = "Check system health and show me CPU, RAM, and temperature"
        intent_lower = intent.lower()
        
        print(f"\n🎯 Testing intent: {intent}")
        print(f"🔤 Lowercase: {intent_lower}")
        
        # Check each agent's triggers
        for agent in registry.get_all():
            print(f"\n📋 Agent: {agent.name}")
            triggers = agent.get_triggers()
            
            for trigger in triggers:
                if trigger.trigger_type == "user_intent":
                    condition = trigger.condition.lower()
                    priority = trigger.priority
                    
                    print(f"   🔧 Trigger: {condition}")
                    print(f"   ⭐ Priority: {priority}")
                    
                    # Check keyword matches
                    keywords = condition.split()
                    matches = sum(1 for kw in keywords if kw in intent_lower)
                    
                    print(f"   🎯 Keywords: {keywords}")
                    print(f"   ✅ Matches: {matches}")
                    
                    if matches > 0:
                        score = (matches * priority) / 10.0
                        print(f"   📊 Score: {score}")
        
        # Test trigger-based routing directly
        print(f"\n🔄 Testing trigger-based routing...")
        
        best_match = None
        best_score = 0
        
        for agent in registry.get_all():
            triggers = agent.get_triggers()
            score = 0
            
            for trigger in triggers:
                if trigger.trigger_type == "user_intent":
                    condition = trigger.condition.lower()
                    priority = trigger.priority
                    
                    # Simple keyword matching for fallback
                    keywords = condition.split()
                    matches = sum(1 for kw in keywords if kw in intent_lower)
                    
                    # Weight matches by priority
                    if matches > 0:
                        score += (matches * priority) / 10.0
                        print(f"   🎯 {agent.name}: {matches} matches, score {score}")
            
            if score > best_score:
                best_score = score
                best_match = agent.name
        
        print(f"\n🏆 Best match: {best_match} (score: {best_score})")
        
        return best_match == "SENTINEL_AGENT"
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_routing())
    print(f"\n🎉 Debug result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
