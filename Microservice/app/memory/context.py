"""
Context Memory - Session State Management

Tracks:
- Last action executed
- Active application
- Action history
- User preferences

Enables contextual commands like:
- "do that again"
- "lower it more"
- "type hello" (knows which window is active)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque


class SessionContext:
    """
    Maintains context for a user session.
    Enables intelligent follow-up commands.
    """
    
    def __init__(self, session_id: str, max_history: int = 50):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # Last action for "do that again"
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_command: Optional[str] = None
        
        # Active application context
        self.active_app: Optional[str] = None
        
        # Vision observations (from recovery system)
        self.vision_observations: List[str] = []
        self.focused_window: Optional[str] = None
        self.focused_process: Optional[str] = None
        self.open_apps: List[str] = []
        self.ui_elements: List[str] = []
        
        # Action history (circular buffer)
        self.history: deque = deque(maxlen=max_history)
        
        # User preferences (learned over time)
        self.preferences: Dict[str, Any] = {
            "default_browser": "chrome",
            "default_volume_step": 10,
            "default_brightness_step": 10,
        }
    
    def update(self, command: str, action: Dict[str, Any], result: Optional[Dict[str, Any]] = None):
        """Update context after action execution."""
        self.last_command = command
        self.last_action = action
        self.last_updated = datetime.now()
        
        # Track active app
        if action.get("action") == "open_app":
            self.active_app = action.get("target", "").replace(".exe", "")
        elif action.get("action") == "close_app":
            if self.active_app == action.get("target", "").replace(".exe", ""):
                self.active_app = None
        
        # Add to history
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "action": action,
            "result": result,
        })
    
    def get_last_action(self) -> Optional[Dict[str, Any]]:
        """Get last executed action for replay."""
        return self.last_action
    
    def get_context_summary(self) -> str:
        """Get context summary for LLM prompt."""
        parts = []
        
        if self.last_action:
            parts.append(f"Last action: {self.last_action.get('action', 'unknown')}")
        
        if self.active_app:
            parts.append(f"Active app: {self.active_app}")
        
        if self.last_command:
            parts.append(f"Last command: '{self.last_command}'")
        
        return "; ".join(parts) if parts else "No prior context"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dict for Intent Analyzer."""
        return {
            "last_action": self.last_action,
            "last_command": self.last_command,
            "active_app": self.active_app,
            "focused_window": self.focused_window,
            "focused_process": self.focused_process,
            "open_apps": self.open_apps,
            "ui_elements": self.ui_elements,
            "vision_observations": self.vision_observations[-3:] if self.vision_observations else [],
            "preferences": self.preferences,
        }
    
    def add_vision_observation(self, observation: str):
        """Add observation from Vision system."""
        self.vision_observations.append(observation)
        # Keep last 10
        if len(self.vision_observations) > 10:
            self.vision_observations = self.vision_observations[-10:]
    
    def update_focused_window(self, window: str, process: str):
        """Update focused window info from C#."""
        self.focused_window = window
        self.focused_process = process


# ===== SESSION STORE =====
# In-memory session storage (could be Redis in production)

_sessions: Dict[str, SessionContext] = {}


def get_session(session_id: str) -> SessionContext:
    """Get or create session context."""
    if session_id not in _sessions:
        _sessions[session_id] = SessionContext(session_id)
        print(f"[CONTEXT] New session: {session_id}")
    return _sessions[session_id]


def update_session(session_id: str, command: str, action: Dict[str, Any], result: Optional[Dict[str, Any]] = None):
    """Update session after action execution."""
    session = get_session(session_id)
    session.update(command, action, result)


def get_context_for_llm(session_id: str) -> Dict[str, Any]:
    """Get context dict for Intent Analyzer."""
    session = get_session(session_id)
    return session.to_dict()


def clear_session(session_id: str):
    """Clear session context."""
    if session_id in _sessions:
        del _sessions[session_id]
        print(f"[CONTEXT] Cleared session: {session_id}")


# ===== CONTEXTUAL COMMAND HANDLERS =====

def is_contextual_command(command: str) -> bool:
    """Check if command requires context."""
    contextual_phrases = [
        "again", "that again", "do that again", "repeat",
        "more", "it more", "lower it", "raise it", "increase it", "decrease it",
        "same", "same thing", "one more time",
    ]
    cmd_lower = command.lower().strip()
    return any(phrase in cmd_lower for phrase in contextual_phrases)


def resolve_contextual_command(command: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Resolve contextual command using session context.
    
    Returns modified action if resolvable, None otherwise.
    """
    session = get_session(session_id)
    cmd_lower = command.lower().strip()
    
    # "do that again" / "repeat"
    if any(x in cmd_lower for x in ["again", "repeat", "same thing", "one more time"]):
        if session.last_action:
            print(f"[CONTEXT] Repeating last action: {session.last_action}")
            return session.last_action
    
    # "more" / "it more" modifiers
    if "more" in cmd_lower and session.last_action:
        last_action = session.last_action.get("action", "")
        
        # Volume context
        if last_action in ["volume_up", "volume_down"]:
            return {
                "action": last_action,
                "amount": session.preferences.get("default_volume_step", 10)
            }
        
        # Brightness context
        if last_action in ["brightness_up", "brightness_down"]:
            return {
                "action": last_action,
                "amount": session.preferences.get("default_brightness_step", 10)
            }
    
    return None
