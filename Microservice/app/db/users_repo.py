"""
Users Repository - Firestore Implementation

Manages user profile documents in Firestore.
Collection: users/{userId}

Syncs Firebase Auth users to Firestore application data.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)


def _get_users_collection():
    """Get the users collection reference."""
    db = get_firestore_client()
    return db.collection('users')


def create_user(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    photo_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new user document in Firestore.
    
    Called on first login to sync Firebase Auth → Firestore.
    
    Args:
        user_id: Firebase Auth UID
        email: User's email address
        name: Display name
        photo_url: Profile photo URL
        
    Returns:
        The created user document data
    """
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "email": email,
        "name": name or "User",
        "photoURL": photo_url,
        "createdAt": now,
        "lastLogin": now,
        "plan": "free"  # Default plan for new users
    }
    
    collection = _get_users_collection()
    collection.document(user_id).set(user_doc)
    
    logger.info(f"[USERS] Created user document: {user_id}")
    return user_doc


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user's profile by their ID.
    
    Args:
        user_id: Firebase Auth UID
        
    Returns:
        User profile dictionary or None if not found
    """
    collection = _get_users_collection()
    doc = collection.document(user_id).get()
    
    if doc.exists:
        data = doc.to_dict()
        data["id"] = user_id  # Include ID in response
        return data
    return None


def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a user's profile with new values.
    
    Args:
        user_id: Firebase Auth UID
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False if user not found
    """
    collection = _get_users_collection()
    doc_ref = collection.document(user_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        logger.warning(f"[USERS] User not found: {user_id}")
        return False
    
    # Filter out protected fields that shouldn't be updated
    protected_fields = {"id", "createdAt"}
    safe_updates = {k: v for k, v in updates.items() if k not in protected_fields}
    
    doc_ref.update(safe_updates)
    logger.info(f"[USERS] Updated user: {user_id}")
    return True


def update_last_login(user_id: str) -> bool:
    """
    Update the last login timestamp for a user.
    
    Args:
        user_id: Firebase Auth UID
        
    Returns:
        True if successful, False if user not found
    """
    now = datetime.now(timezone.utc).isoformat()
    
    collection = _get_users_collection()
    doc_ref = collection.document(user_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False
    
    doc_ref.update({"lastLogin": now})
    return True


def delete_user(user_id: str) -> bool:
    """
    Delete a user's profile document.
    
    Note: This does NOT delete subcollections (skills, sessions, etc.)
    Subcollection deletion should be handled separately.
    
    Args:
        user_id: Firebase Auth UID
        
    Returns:
        True if deleted, False if not found
    """
    collection = _get_users_collection()
    doc_ref = collection.document(user_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        logger.warning(f"[USERS] User not found for deletion: {user_id}")
        return False
    
    doc_ref.delete()
    logger.info(f"[USERS] Deleted user: {user_id}")
    return True
