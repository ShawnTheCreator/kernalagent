"""
Settings Repository - Firestore Implementation

Manages user settings/preferences in Firestore.
Collection: users/{userId}/settings/preferences

Stores user preferences like theme, execution mode, etc.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)


def _get_settings_doc(user_id: str):
    """Get the settings document reference for a user."""
    db = get_firestore_client()
    return db.collection('users').document(user_id).collection('settings').document('preferences')


def get_default_settings() -> Dict[str, Any]:
    """
    Returns default settings for new users.
    
    Returns:
        Dictionary with default setting values
    """
    return {
        "theme": "dark",
        "executionMode": "MOCK",  # MOCK, LIVE
        "confirmActions": True,
        "language": "en",
        "notificationsEnabled": True,
        "autoSaveSkills": True
    }


def get_settings(user_id: str) -> Dict[str, Any]:
    """
    Get user settings. Creates defaults if not exists.
    
    Args:
        user_id: Firebase Auth UID
        
    Returns:
        User settings dictionary
    """
    doc_ref = _get_settings_doc(user_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    
    # Create default settings on first access
    defaults = get_default_settings()
    defaults["createdAt"] = datetime.now(timezone.utc).isoformat()
    doc_ref.set(defaults)
    
    logger.info(f"[SETTINGS] Created default settings for user: {user_id}")
    return defaults


def update_settings(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update user settings with new values.
    
    Args:
        user_id: Firebase Auth UID
        updates: Dictionary of settings to update
        
    Returns:
        Updated settings dictionary
    """
    doc_ref = _get_settings_doc(user_id)
    
    # Add updatedAt timestamp
    updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Filter out protected fields
    protected_fields = {"createdAt"}
    safe_updates = {k: v for k, v in updates.items() if k not in protected_fields}
    
    # Ensure settings document exists (merge with existing or create)
    doc_ref.set(safe_updates, merge=True)
    
    logger.info(f"[SETTINGS] Updated settings for user: {user_id}")
    
    # Return merged settings
    return doc_ref.get().to_dict()


def reset_settings(user_id: str) -> Dict[str, Any]:
    """
    Reset user settings to defaults.
    
    Args:
        user_id: Firebase Auth UID
        
    Returns:
        Default settings dictionary
    """
    doc_ref = _get_settings_doc(user_id)
    
    defaults = get_default_settings()
    defaults["createdAt"] = datetime.now(timezone.utc).isoformat()
    defaults["resetAt"] = datetime.now(timezone.utc).isoformat()
    
    doc_ref.set(defaults)
    
    logger.info(f"[SETTINGS] Reset settings for user: {user_id}")
    return defaults
