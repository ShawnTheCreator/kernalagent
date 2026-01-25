"""
Create a test skill for the user in Firebase.
Run this from the Microservice directory with the venv activated.
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.db.firebase_client import get_user_skills_collection

# User ID from Firebase console screenshot
USER_ID = "FpOGm1L6IHVdySLg8tbY4I36Fw2"

# Create test skill
test_skill = {
    "name": "Test Skill - Open Calculator",
    "intent_signature": "open calculator",
    "description": "Opens the Windows Calculator application",
    "confidence": 0.95,
    "success_count": 5,
    "failure_count": 0,
    "created_at": datetime.now().isoformat(),
    "last_used_at": datetime.now().isoformat(),
    "steps": [
        {"action": "press_keys", "keys": "win", "description": "Open start menu"},
        {"action": "type_text", "text": "calculator", "description": "Type calculator"},
        {"action": "press_keys", "keys": "enter", "description": "Launch calculator"}
    ],
    "tags": ["utility", "test"]
}

print(f"Creating test skill for user: {USER_ID}")
print(f"Skill name: {test_skill['name']}")

try:
    # Get user's skills collection
    skills_ref = get_user_skills_collection(USER_ID)
    
    # Add the skill
    doc_ref = skills_ref.add(test_skill)
    
    print(f"\n✅ Test skill created successfully!")
    print(f"   Skill ID: {doc_ref[1].id}")
    print(f"   Path: users/{USER_ID}/skills/{doc_ref[1].id}")
    
except Exception as e:
    print(f"\n❌ Error creating skill: {e}")
    import traceback
    traceback.print_exc()
