#!/usr/bin/env python3
"""
Debug the registry singleton issue.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def debug_registry_singleton():
    """Debug registry singleton behavior."""
    print("🔍 Debug Registry Singleton")
    print("=" * 50)
    
    try:
        # Test multiple calls to get_registry
        from agents.agent_registry import get_registry, AgentRegistry
        
        print("📋 Testing get_registry() calls...")
        
        reg1 = get_registry()
        reg2 = get_registry()
        reg3 = get_registry()
        
        print(f"   Registry 1: {id(reg1)}")
        print(f"   Registry 2: {id(reg2)}")
        print(f"   Registry 3: {id(reg3)}")
        print(f"   All same: {reg1 is reg2 is reg3}")
        
        # Test direct class access
        print(f"\n📋 Testing direct class access...")
        reg4 = AgentRegistry.get_instance()
        reg5 = AgentRegistry.get_instance()
        
        print(f"   Direct 1: {id(reg4)}")
        print(f"   Direct 2: {id(reg5)}")
        print(f"   Direct same: {reg4 is reg5}")
        print(f"   Cross same: {reg1 is reg4}")
        
        # Test instance variable
        print(f"\n📋 Testing class variable...")
        print(f"   AgentRegistry._instance: {id(AgentRegistry._instance)}")
        print(f"   AgentRegistry._instance is reg1: {AgentRegistry._instance is reg1}")
        
        # Test importing router first
        print(f"\n📋 Testing import order issue...")
        
        # Clear the singleton
        AgentRegistry._instance = None
        
        # Import router (this might create a registry)
        print("   Importing router...")
        from agents.intelligent_router import IntelligentRouter
        
        # Check registry now
        reg6 = get_registry()
        print(f"   Registry after router import: {id(reg6)}")
        print(f"   AgentRegistry._instance: {id(AgentRegistry._instance)}")
        
        # Create router instance
        print("   Creating router instance...")
        router = IntelligentRouter()
        print(f"   Router registry: {id(router._registry)}")
        print(f"   Router registry is same: {router._registry is reg6}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_registry_singleton()
    print(f"\n🎉 Debug result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
