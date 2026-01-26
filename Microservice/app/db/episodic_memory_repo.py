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


async def search_memories(
    user_id: str,
    query: str,
    event_types: Optional[List[str]] = None,
    limit: int = 20,
    before_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search through memories for specific content.
    
    Args:
        user_id: Session/user identifier
        query: Search query string
        event_types: Filter by event types (chat_user, chat_agent, action_tool, etc.)
        limit: Maximum results to return
        before_timestamp: Search only before this timestamp
    
    Returns:
        List of matching memory events with relevance scores
    """
    try:
        # Get all memories first
        events = await get_timeline(user_id, limit=100, before_timestamp=before_timestamp)
        
        # Filter by event types if specified
        if event_types:
            events = [e for e in events if e.get('type') in event_types]
        
        # Search and rank results
        matches = []
        query_lower = query.lower()
        
        for event in events:
            content = event.get('content', '').lower()
            metadata = event.get('metadata', {})
            
            # Calculate relevance score
            score = 0
            
            # Exact match gets highest score
            if query_lower in content:
                score += 10
                
            # Word matches
            query_words = query_lower.split()
            content_words = content.split()
            
            for word in query_words:
                if word in content_words:
                    score += 2
                    
            # Metadata matches
            for key, value in metadata.items():
                if isinstance(value, str) and query_lower in value.lower():
                    score += 1
            
            # Action-specific matching
            if event.get('type') == 'action_tool':
                if 'open' in query_lower and 'opened' in content:
                    score += 3
                elif 'chrome' in query_lower and 'chrome' in content.lower():
                    score += 3
                elif 'notepad' in query_lower and 'notepad' in content.lower():
                    score += 3
            
            if score > 0:
                matches.append({
                    **event,
                    'relevance_score': score,
                    'matched_content': content
                })
        
        # Sort by relevance score (highest first) and limit
        matches.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        logger.info(f"[TIMELINE] Search '{query}' found {len(matches)} matches for {user_id}")
        return matches[:limit]
        
    except Exception as e:
        logger.error(f"[TIMELINE] Failed to search memories: {e}")
        return []


async def get_memory_summary(
    user_id: str,
    limit: int = 50,
    include_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a summary of memories for a session.
    
    Args:
        user_id: Session/user identifier
        limit: Number of recent events to analyze
        include_types: Specific event types to include
    
    Returns:
        Dictionary with summary statistics and key events
    """
    try:
        events = await get_timeline(user_id, limit)
        
        if include_types:
            events = [e for e in events if e.get('type') in include_types]
        
        # Analyze events
        summary = {
            'total_events': len(events),
            'event_types': {},
            'automation_actions': [],
            'recent_conversations': [],
            'time_span': None,
            'key_activities': []
        }
        
        # Count event types
        for event in events:
            event_type = event.get('type', 'unknown')
            summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
        
        # Extract automation actions
        for event in events:
            if event.get('type') == 'action_tool':
                summary['automation_actions'].append({
                    'content': event.get('content', ''),
                    'timestamp': event.get('timestamp', ''),
                    'metadata': event.get('metadata', {})
                })
        
        # Extract recent conversations
        for event in events[:5]:  # Last 5 conversations
            if event.get('type') in ['chat_user', 'chat_agent']:
                summary['recent_conversations'].append({
                    'type': event.get('type'),
                    'content': event.get('content', '')[:100] + '...',
                    'timestamp': event.get('timestamp', '')
                })
        
        # Calculate time span
        if events:
            timestamps = [e.get('timestamp', '') for e in events if e.get('timestamp')]
            if timestamps:
                summary['time_span'] = {
                    'first': timestamps[-1],
                    'last': timestamps[0]
                }
        
        # Identify key activities
        app_opens = [e for e in events if 'opened' in e.get('content', '').lower()]
        if app_opens:
            summary['key_activities'].append(f"Opened {len(app_opens)} applications")
        
        chat_count = len([e for e in events if e.get('type') == 'chat_user'])
        if chat_count > 0:
            summary['key_activities'].append(f"Had {chat_count} conversations")
        
        logger.info(f"[TIMELINE] Generated summary for {user_id}: {summary['total_events']} events")
        return summary
        
    except Exception as e:
        logger.error(f"[TIMELINE] Failed to generate memory summary: {e}")
        return {
            'total_events': 0,
            'event_types': {},
            'automation_actions': [],
            'recent_conversations': [],
            'time_span': None,
            'key_activities': []
        }
