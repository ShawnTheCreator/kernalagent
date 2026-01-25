"""
Episodic Memory Repository - Timeline of Events

Stores a chronological timeline of all agent activities, thoughts, and user interactions.
Collection: users/{userId}/timeline

Event Types:
- chat_user: User message
- chat_agent: Agent response
- action_tool: Tool execution (Janitor, etc.)
- memory_thought: Internal reasoning/thought
- system_alert: Errors or notifications
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Literal
import logging
import uuid

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)

EventType = Literal["chat_user", "chat_agent", "action_tool", "memory_thought", "system_alert"]

class TimelineEvent:
    def __init__(
        self,
        event_type: EventType,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.content = content
        self.user_id = user_id
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.event_id,
            "type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.timestamp  # For Firestore ordering
        }

# In-memory storage for local dev/testing without Firebase
_LOCAL_TIMELINE = {}

def _get_timeline_collection(user_id: str):
    """Get the timeline collection for a user (or mock)."""
    try:
        db = get_firestore_client()
        return db.collection('users').document(user_id).collection('timeline')
    except Exception:
        # Fallback to local in-memory mock
        logger.warning("[TIMELINE] Using in-memory mock (No Firebase)")
        return None

async def log_event(
    user_id: str,
    event_type: EventType,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a new event to the timeline.
    """
    try:
        event = TimelineEvent(event_type, content, user_id, metadata)
        col = _get_timeline_collection(user_id)
        
        if col:
            # Add to Firestore
            col.document(event.event_id).set(event.to_dict())
        else:
            # Add to local mock
            if user_id not in _LOCAL_TIMELINE:
                _LOCAL_TIMELINE[user_id] = []
            _LOCAL_TIMELINE[user_id].append(event.to_dict())
        
        logger.info(f"[TIMELINE] Logged {event_type}: {content[:50]}...")
        return event.event_id
        
    except Exception as e:
        logger.error(f"[TIMELINE] Failed to log event: {e}")
        return ""

async def get_timeline(
    user_id: str, 
    limit: int = 50, 
    before_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent timeline events.
    """
    try:
        col = _get_timeline_collection(user_id)
        
        if col:
            query = col.order_by("created_at", direction="DESCENDING").limit(limit)
            docs = query.stream()
            events = [doc.to_dict() for doc in docs]
            return events
        else:
            # Return from local mock (sorted new -> old)
            events = _LOCAL_TIMELINE.get(user_id, [])
            # Sort by timestamp desc
            events.sort(key=lambda x: x['timestamp'], reverse=True)
            return events[:limit]
            
    except Exception as e:
        logger.error(f"[TIMELINE] Failed to fetch timeline: {e}")
        return []

async def clear_timeline(user_id: str) -> bool:
    """Clear all events for a user."""
    try:
        col = _get_timeline_collection(user_id)
        
        if col:
            # Batch delete
            batch_size = 100
            delete_done = False
            
            while not delete_done:
                docs = list(col.limit(batch_size).stream())
                if not docs:
                    break
                    
                for doc in docs:
                    doc.reference.delete()
                    
                if len(docs) < batch_size:
                    delete_done = True
        else:
            # Clear local mock
            if user_id in _LOCAL_TIMELINE:
                _LOCAL_TIMELINE[user_id] = []
                
        logger.info(f"[TIMELINE] Cleared timeline for {user_id}")
        return True
    except Exception as e:
        logger.error(f"[TIMELINE] Failed to clear timeline: {e}")
        return False
