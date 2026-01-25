"""
Verify Memory Integration

Tests that user's frequent skills get a confidence boost in the decision engine.
"""
import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.getcwd())

from app.agent.decision_engine import select_best_skill

# Mock data
MOCK_SKILLS = [
    {
        "id": "skill_1",
        "name": "organize_downloads",
        "intent_signature": "clean downloads folder",
        "success_count": 0,
        "last_used_at": None
    },
    {
        "id": "skill_2",
        "name": "check_weather",
        "intent_signature": "check weather report",
        "success_count": 0,
        "last_used_at": None
    }
]

def test_memory_boost():
    print("🧠 TESTING MEMORY INTEGRATION")
    print("-" * 40)
    
    intent = "organize my files" 
    # This intent is somewhat similar to "clean downloads folder" but maybe weak match
    
    # 1. Test WITHOUT memory
    print("\n[Test 1] Without Memory:")
    match_no_mem = select_best_skill(intent, MOCK_SKILLS)
    if match_no_mem:
        print(f"   Match: {match_no_mem['skill']['name']}")
        print(f"   Score: {match_no_mem['score']:.4f}")
    else:
        print("   No match found (score too low)")
        
    # 2. Test WITH memory (frequent skill)
    print("\n[Test 2] With Memory (organize_downloads is frequent):")
    user_context = {
        "frequent_skills": ["organize_downloads"]
    }
    
    match_mem = select_best_skill(intent, MOCK_SKILLS, user_context)
    if match_mem:
        print(f"   Match: {match_mem['skill']['name']}")
        print(f"   Score: {match_mem['score']:.4f}")
        print(f"   Is Frequent: {match_mem.get('is_frequent')}")
        
        if match_mem.get('is_frequent') and match_mem['score'] > (match_no_mem['score'] if match_no_mem else 0):
            print("\n✅ SUCCESS: Memory boost applied!")
        else:
            print("\n❌ FAILURE: Score did not increase appropriately")
    else:
        print("   No match found")

if __name__ == "__main__":
    test_memory_boost()
