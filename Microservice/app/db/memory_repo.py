"""
Memory Repository - Firestore Implementation

Manages long-term agent memory per user.
Collection: users/{userId}/memory/{memoryType}

Stores persistent patterns, frequently used skills, and failure patterns.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)


def _get_memory_collection(user_id: str):
    """Get the memory collection reference for a user."""
    db = get_firestore_client()
    return db.collection('users').document(user_id).collection('memory')


def get_memory(user_id: str, memory_type: str = "long_term") -> Dict[str, Any]:
    """
    Get a memory document by type. Creates empty if not exists.
    
    Args:
        user_id: Firebase Auth UID
        memory_type: Type of memory (long_term, patterns, preferences)
        
    Returns:
        Memory document dictionary
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document(memory_type)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    
    # Create empty memory document
    now = datetime.now(timezone.utc).isoformat()
    empty_memory = {
        "frequent_skills": [],
        "failure_patterns": [],
        "success_patterns": [],
        "created_at": now,
        "updated_at": now
    }
    
    doc_ref.set(empty_memory)
    logger.info(f"[MEMORY] Created empty {memory_type} memory for user: {user_id}")
    return empty_memory


def update_memory(user_id: str, memory_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a memory document with new data.
    
    Args:
        user_id: Firebase Auth UID
        memory_type: Type of memory
        data: Data to merge into memory
        
    Returns:
        Updated memory document
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document(memory_type)
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    doc_ref.set(data, merge=True)
    
    logger.info(f"[MEMORY] Updated {memory_type} memory for user: {user_id}")
    return doc_ref.get().to_dict()


def add_frequent_skill(user_id: str, skill_name: str, max_skills: int = 10) -> bool:
    """
    Add or bump a skill to the frequent skills list.
    
    Maintains a list of top N most frequently used skills.
    
    Args:
        user_id: Firebase Auth UID
        skill_name: Name of the skill
        max_skills: Maximum skills to track
        
    Returns:
        True if successful
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document("long_term")
    doc = doc_ref.get()
    
    now = datetime.now(timezone.utc).isoformat()
    
    if doc.exists:
        data = doc.to_dict()
        frequent_skills = data.get("frequent_skills", [])
        
        # Remove if already exists (will add to front)
        frequent_skills = [s for s in frequent_skills if s != skill_name]
        
        # Add to front (most recent)
        frequent_skills.insert(0, skill_name)
        
        # Trim to max
        frequent_skills = frequent_skills[:max_skills]
        
        doc_ref.update({
            "frequent_skills": frequent_skills,
            "updated_at": now
        })
    else:
        # Create new memory with this skill
        doc_ref.set({
            "frequent_skills": [skill_name],
            "failure_patterns": [],
            "success_patterns": [],
            "created_at": now,
            "updated_at": now
        })
    
    logger.info(f"[MEMORY] Added frequent skill '{skill_name}' for user: {user_id}")
    return True


def add_failure_pattern(user_id: str, pattern: str, max_patterns: int = 20) -> bool:
    """
    Add a failure pattern to track recurring issues.
    
    Args:
        user_id: Firebase Auth UID
        pattern: Description of the failure pattern
        max_patterns: Maximum patterns to track
        
    Returns:
        True if successful
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document("long_term")
    doc = doc_ref.get()
    
    now = datetime.now(timezone.utc).isoformat()
    
    if doc.exists:
        data = doc.to_dict()
        failure_patterns = data.get("failure_patterns", [])
        
        # Add if not already present
        if pattern not in failure_patterns:
            failure_patterns.insert(0, pattern)
            failure_patterns = failure_patterns[:max_patterns]
            
            doc_ref.update({
                "failure_patterns": failure_patterns,
                "updated_at": now
            })
    else:
        doc_ref.set({
            "frequent_skills": [],
            "failure_patterns": [pattern],
            "success_patterns": [],
            "created_at": now,
            "updated_at": now
        })
    
    logger.info(f"[MEMORY] Added failure pattern for user: {user_id}")
    return True


def add_success_pattern(user_id: str, pattern: str, max_patterns: int = 20) -> bool:
    """
    Add a success pattern to track effective strategies.
    
    Args:
        user_id: Firebase Auth UID
        pattern: Description of the success pattern
        max_patterns: Maximum patterns to track
        
    Returns:
        True if successful
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document("long_term")
    doc = doc_ref.get()
    
    now = datetime.now(timezone.utc).isoformat()
    
    if doc.exists:
        data = doc.to_dict()
        success_patterns = data.get("success_patterns", [])
        
        if pattern not in success_patterns:
            success_patterns.insert(0, pattern)
            success_patterns = success_patterns[:max_patterns]
            
            doc_ref.update({
                "success_patterns": success_patterns,
                "updated_at": now
            })
    else:
        doc_ref.set({
            "frequent_skills": [],
            "failure_patterns": [],
            "success_patterns": [pattern],
            "created_at": now,
            "updated_at": now
        })
    
    logger.info(f"[MEMORY] Added success pattern for user: {user_id}")
    return True


def clear_memory(user_id: str, memory_type: str = "long_term") -> bool:
    """
    Clear a specific memory type for a user.
    
    Args:
        user_id: Firebase Auth UID
        memory_type: Type of memory to clear
        
    Returns:
        True if successful
    """
    collection = _get_memory_collection(user_id)
    doc_ref = collection.document(memory_type)
    
    now = datetime.now(timezone.utc).isoformat()
    doc_ref.set({
        "frequent_skills": [],
        "failure_patterns": [],
        "success_patterns": [],
        "cleared_at": now,
        "updated_at": now
    })
    
    logger.info(f"[MEMORY] Cleared {memory_type} memory for user: {user_id}")
    return True
