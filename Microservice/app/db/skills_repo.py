"""
Skills Repository - Firebase Firestore Implementation

Stores and retrieves learned skills from Firebase Firestore.
Replaces SQLite implementation for cross-platform skill sharing.

Firestore Collection: skills
"""
import uuid
from datetime import datetime
from typing import Optional

from .firebase_client import get_skills_collection


def save_skill(name: str, intent_signature: str, steps: list, description: str, confidence: str, is_global: bool = True) -> str:
    """
    Save a new skill to Firestore.
    
    Args:
        name: Human-readable skill name (e.g., "Export as PDF")
        intent_signature: The intent pattern that triggers this skill
        steps: List of step dictionaries with action details
        
    Returns:
        The generated skill ID
    """
    skill_id = name.replace(" ", "_").lower()
    now = datetime.utcnow().isoformat() + "Z"
    
    skill_doc = {
        "id": skill_id,
        "name": name,
        "intent_signature": intent_signature,
        "steps": steps,
        "description": description,
        "confidence": confidence,
        "created_at": now,
        "lastExecuted": None,
        "executionCount": 0,
        "is_global": is_global
    }
    
    # Save to Firestore with skill_id as document ID
    collection = get_skills_collection()
    collection.document(skill_id).set(skill_doc)
    
    print(f"[SKILLS DB] Saved skill: {name} (ID: {skill_id})")
    return skill_id


def get_all_skills() -> list:
    """
    Retrieve all skills from Firestore.
    
    Returns:
        List of all skill dictionaries
    """
    collection = get_skills_collection()
    docs = collection.stream()
    
    skills = []
    for doc in docs:
        skill_data = doc.to_dict()
        skills.append(skill_data)
    
    print(f"[SKILLS DB] Retrieved {len(skills)} skills")
    return skills


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """
    Get a single skill by its ID.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        Skill dictionary or None if not found
    """
    collection = get_skills_collection()
    doc = collection.document(skill_id).get()
    
    if doc.exists:
        return doc.to_dict()
    return None


def get_skills_by_intent(intent_signature: str) -> list:
    """
    Find skills that match the given intent (fuzzy search).
    
    Args:
        intent_signature: The intent pattern to search for
        
    Returns:
        List of matching skill dictionaries
    """
    # Get all skills and filter locally (Firestore doesn't support LIKE queries)
    all_skills = get_all_skills()
    search_lower = intent_signature.lower()
    
    matching = [
        skill for skill in all_skills
        if search_lower in skill.get('intent_signature', '').lower()
        or search_lower in skill.get('name', '').lower()
    ]
    
    print(f"[SKILLS DB] Found {len(matching)} skills matching '{intent_signature}'")
    return matching


def increment_skill_usage(skill_id: str) -> bool:
    """
    Increment the success_count and update last_used_at for a skill.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        True if successful, False if skill not found
    """
    collection = get_skills_collection()
    doc_ref = collection.document(skill_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"[SKILLS DB] Skill not found: {skill_id}")
        return False
    
    now = datetime.utcnow().isoformat() + "Z"
    current_data = doc.to_dict()
    new_count = current_data.get('success_count', 0) + 1
    
    doc_ref.update({
        "last_used_at": now,
        "success_count": new_count
    })
    
    print(f"[SKILLS DB] Incremented usage for skill: {skill_id} (count: {new_count})")
    return True


def delete_skill(skill_id: str) -> bool:
    """
    Delete a skill by its ID.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        True if deleted, False if not found
    """
    collection = get_skills_collection()
    doc_ref = collection.document(skill_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"[SKILLS DB] Skill not found for deletion: {skill_id}")
        return False
    
    doc_ref.delete()
    print(f"[SKILLS DB] Deleted skill: {skill_id}")
    return True


def update_skill(skill_id: str, updates: dict) -> bool:
    """
    Update a skill with new values.
    
    Args:
        skill_id: The skill's unique ID
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False if skill not found
    """
    collection = get_skills_collection()
    doc_ref = collection.document(skill_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"[SKILLS DB] Skill not found: {skill_id}")
        return False
    
    doc_ref.update(updates)
    print(f"[SKILLS DB] Updated skill: {skill_id}")
    return True
