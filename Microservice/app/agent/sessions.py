"""
Agent Session Storage

In-memory storage for agent sessions.
Tracks session state, decisions, and timeline for explainability.

Sessions are stored in memory only (not persisted to Firebase).
This is intentional - sessions are ephemeral previews.
"""
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class TimelineEntry:
    """A single entry in the session timeline."""
    strategy: str
    skill: Optional[str]
    action: str
    confidence: float
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class AgentSession:
    """
    Represents a single agent preview session.
    
    Sessions track the agent's reasoning process for a given intent.
    """
    session_id: str
    intent: str
    timeline: List[TimelineEntry] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, FAILED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# In-memory session store
# Key: session_id, Value: AgentSession
_sessions: Dict[str, AgentSession] = {}


def create_session(intent: str) -> AgentSession:
    """
    Create a new agent session for the given intent.
    
    Args:
        intent: The user's intent (e.g., "scroll down the page")
        
    Returns:
        New AgentSession instance
    """
    session_id = str(uuid.uuid4())
    session = AgentSession(
        session_id=session_id,
        intent=intent
    )
    _sessions[session_id] = session
    print(f"[SESSION] Created session: {session_id} for intent: '{intent}'")
    return session


def get_session(session_id: str) -> Optional[AgentSession]:
    """
    Retrieve a session by ID.
    
    Args:
        session_id: The session's unique ID
        
    Returns:
        AgentSession or None if not found
    """
    return _sessions.get(session_id)


def add_timeline_entry(
    session_id: str,
    strategy: str,
    skill: Optional[str],
    action: str,
    confidence: float,
    reason: str
) -> bool:
    """
    Add a decision entry to the session timeline.
    
    Args:
        session_id: The session ID
        strategy: Decision strategy (REUSE_SKILL, ADAPT_SKILL, FRESH_REASONING)
        skill: Skill name if applicable
        action: Action type (CLICK, SCROLL, TYPE, etc.)
        confidence: Confidence level (0.0 - 1.0)
        reason: Explanation for the decision
        
    Returns:
        True if added, False if session not found
    """
    session = _sessions.get(session_id)
    if session is None:
        return False
    
    entry = TimelineEntry(
        strategy=strategy,
        skill=skill,
        action=action,
        confidence=confidence,
        reason=reason
    )
    session.timeline.append(entry)
    print(f"[SESSION] Added timeline entry to {session_id}: {action}")
    return True


def complete_session(session_id: str, status: str = "COMPLETED") -> bool:
    """
    Mark a session as completed.
    
    Args:
        session_id: The session ID
        status: Final status (COMPLETED or FAILED)
        
    Returns:
        True if updated, False if session not found
    """
    session = _sessions.get(session_id)
    if session is None:
        return False
    
    session.status = status
    print(f"[SESSION] Session {session_id} marked as {status}")
    return True


def session_to_dict(session: AgentSession) -> dict:
    """
    Convert an AgentSession to a dictionary for API response.
    
    Args:
        session: The AgentSession to convert
        
    Returns:
        Dictionary representation
    """
    return {
        "session_id": session.session_id,
        "intent": session.intent,
        "timeline": [
            {
                "strategy": entry.strategy,
                "skill": entry.skill,
                "action": entry.action,
                "confidence": entry.confidence,
                "reason": entry.reason
            }
            for entry in session.timeline
        ],
        "status": session.status
    }
