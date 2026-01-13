"""
Sessions Repository - Firestore Implementation

Manages agent sessions and steps in Firestore.
Collection: users/{userId}/sessions/{sessionId}
Subcollection: users/{userId}/sessions/{sessionId}/steps/{stepId}

Tracks agent reasoning timelines and execution history.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)


def _get_sessions_collection(user_id: str):
    """Get the sessions collection reference for a user."""
    db = get_firestore_client()
    return db.collection('users').document(user_id).collection('sessions')


def _get_steps_collection(user_id: str, session_id: str):
    """Get the steps subcollection reference for a session."""
    db = get_firestore_client()
    return (db.collection('users')
            .document(user_id)
            .collection('sessions')
            .document(session_id)
            .collection('steps'))


def create_session(user_id: str, intent: str) -> Dict[str, Any]:
    """
    Create a new agent session.
    
    Args:
        user_id: Firebase Auth UID
        intent: The user's intent/goal for this session
        
    Returns:
        Created session document with session_id
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    session_doc = {
        "session_id": session_id,
        "intent": intent,
        "started_at": now,
        "ended_at": None,
        "status": "IN_PROGRESS",
        "confidence": 0.0,
        "step_count": 0
    }
    
    collection = _get_sessions_collection(user_id)
    collection.document(session_id).set(session_doc)
    
    logger.info(f"[SESSIONS] Created session: {session_id} for user: {user_id}")
    return session_doc


def get_session(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a session by ID.
    
    Args:
        user_id: Firebase Auth UID
        session_id: Session ID
        
    Returns:
        Session document or None if not found
    """
    collection = _get_sessions_collection(user_id)
    doc = collection.document(session_id).get()
    
    if doc.exists:
        return doc.to_dict()
    return None


def get_recent_sessions(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent sessions for a user, ordered by start time descending.
    
    Args:
        user_id: Firebase Auth UID
        limit: Maximum number of sessions to return
        
    Returns:
        List of session documents
    """
    collection = _get_sessions_collection(user_id)
    docs = (collection
            .order_by("started_at", direction="DESCENDING")
            .limit(limit)
            .stream())
    
    sessions = [doc.to_dict() for doc in docs]
    logger.info(f"[SESSIONS] Retrieved {len(sessions)} sessions for user: {user_id}")
    return sessions


def add_session_step(
    user_id: str,
    session_id: str,
    action: str,
    skill: Optional[str] = None,
    strategy: str = "FRESH_REASONING",
    confidence: float = 0.5,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Add a step to a session's timeline.
    
    Args:
        user_id: Firebase Auth UID
        session_id: Session ID
        action: Action type (CLICK, TYPE, SCROLL, etc.)
        skill: Skill name if reusing
        strategy: REUSE_SKILL, ADAPT_SKILL, FRESH_REASONING
        confidence: Confidence score (0-1)
        reason: Reasoning explanation
        
    Returns:
        Created step document
    """
    step_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    step_doc = {
        "step_id": step_id,
        "action": action,
        "skill": skill,
        "strategy": strategy,
        "confidence": confidence,
        "reason": reason,
        "timestamp": now
    }
    
    # Add step to subcollection
    steps_collection = _get_steps_collection(user_id, session_id)
    steps_collection.document(step_id).set(step_doc)
    
    # Increment step count on session
    sessions_collection = _get_sessions_collection(user_id)
    session_ref = sessions_collection.document(session_id)
    session_doc = session_ref.get()
    
    if session_doc.exists:
        data = session_doc.to_dict()
        new_count = data.get("step_count", 0) + 1
        # Update with latest confidence
        session_ref.update({
            "step_count": new_count,
            "confidence": confidence
        })
    
    logger.info(f"[SESSIONS] Added step to session: {session_id}")
    return step_doc


def get_session_steps(user_id: str, session_id: str) -> List[Dict[str, Any]]:
    """
    Get all steps for a session.
    
    Args:
        user_id: Firebase Auth UID
        session_id: Session ID
        
    Returns:
        List of step documents ordered by timestamp
    """
    steps_collection = _get_steps_collection(user_id, session_id)
    docs = steps_collection.order_by("timestamp").stream()
    
    return [doc.to_dict() for doc in docs]


def complete_session(
    user_id: str,
    session_id: str,
    status: str = "COMPLETED",
    final_confidence: Optional[float] = None
) -> bool:
    """
    Mark a session as complete.
    
    Args:
        user_id: Firebase Auth UID
        session_id: Session ID
        status: Final status (COMPLETED, FAILED, CANCELLED)
        final_confidence: Optional final confidence score
        
    Returns:
        True if successful, False if session not found
    """
    collection = _get_sessions_collection(user_id)
    doc_ref = collection.document(session_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        logger.warning(f"[SESSIONS] Session not found: {session_id}")
        return False
    
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "ended_at": now,
        "status": status
    }
    
    if final_confidence is not None:
        updates["confidence"] = final_confidence
    
    doc_ref.update(updates)
    logger.info(f"[SESSIONS] Completed session: {session_id} with status: {status}")
    return True


def delete_session(user_id: str, session_id: str) -> bool:
    """
    Delete a session and all its steps.
    
    Args:
        user_id: Firebase Auth UID
        session_id: Session ID
        
    Returns:
        True if deleted, False if not found
    """
    collection = _get_sessions_collection(user_id)
    doc_ref = collection.document(session_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False
    
    # Delete all steps first (Firestore doesn't auto-delete subcollections)
    steps_collection = _get_steps_collection(user_id, session_id)
    for step_doc in steps_collection.stream():
        step_doc.reference.delete()
    
    # Delete session document
    doc_ref.delete()
    logger.info(f"[SESSIONS] Deleted session: {session_id}")
    return True
