"""
Test file to debug Gemini's intent parsing.
Run: python test_gemini.py
"""

import asyncio
import os
from app.reasoning.intent_analyzer import get_intent_analyzer

async def test_gemini():
    print("="*80)
    print("TESTING GEMINI INTENT ANALYZER")
    print("="*80)
    
    analyzer = get_intent_analyzer()
    
    test_commands = [
        "open notepad and type Hello World",
        "type hello and press enter",
        "open notepad and type Hello World and press ctrl+s",
        "open notepad and type Hello World and press ctrl+s and type test.txt and press enter",
    ]
    
    for cmd in test_commands:
        print(f"\n{'='*80}")
        print(f"INPUT: {cmd}")
        print("-"*80)
        
        result = await analyzer.analyze(cmd, context=None)
        
        print(f"Intent: {result.get('intent')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Actions ({len(result.get('actions', []))}):")
        
        for i, action in enumerate(result.get('actions', []), 1):
            print(f"  {i}. {action.get('tool')} - {action.get('action')}")
            if action.get('content'):
                print(f"     content=\"{action.get('content')}\"")
            if action.get('target'):
                print(f"     target=\"{action.get('target')}\"")
            if action.get('keys'):
                print(f"     keys=\"{action.get('keys')}\"")
        
        print("\nFull JSON:")
        import json
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_gemini())
