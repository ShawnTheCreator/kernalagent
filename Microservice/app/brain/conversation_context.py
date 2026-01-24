"""
Conversation Context - Multi-turn conversation state management.

Tracks:
- Message history for context
- Pending clarifications
- Last successful intent (for "do that again")
- Session state
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationContext:
    """
    Manages multi-turn conversation state for a session.
    
    Features:
    - Message history with sliding window
    - Pending clarification tracking
    - Last intent memory for follow-ups
    - Context extraction for LLM
    """
    
    MAX_HISTORY = 10  # Keep last N messages for context
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ConversationMessage] = []
        self.pending_clarification: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.last_target: Optional[str] = None
        self.last_action_success: Optional[bool] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_user_message(self, content: str, metadata: Dict[str, Any] = None):
        """Add a user message to the conversation."""
        self.messages.append(ConversationMessage(
            role=MessageRole.USER,
            content=content,
            metadata=metadata or {}
        ))
        self._trim_history()
        self.updated_at = datetime.now()
    
    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None):
        """Add an assistant message to the conversation."""
        self.messages.append(ConversationMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            metadata=metadata or {}
        ))
        self._trim_history()
        self.updated_at = datetime.now()
    
    def set_pending_clarification(self, question: str, about: str):
        """Mark that we're waiting for clarification on something."""
        self.pending_clarification = about
        self.add_assistant_message(question, {"type": "clarification", "about": about})
    
    def resolve_clarification(self, answer: str) -> str:
        """
        Resolve a pending clarification with the user's answer.
        
        Returns the combined intent (e.g., "open" + "chrome" = "open chrome")
        """
        if self.pending_clarification:
            combined = f"{self.pending_clarification} {answer}"
            self.pending_clarification = None
            return combined
        return answer
    
    def set_last_action(self, intent: str, target: str, success: bool):
        """Record the last executed action for "do that again" commands."""
        self.last_intent = intent
        self.last_target = target
        self.last_action_success = success
        self.updated_at = datetime.now()
    
    def get_last_action_description(self) -> Optional[str]:
        """Get a description of the last action for repeating."""
        if self.last_intent and self.last_target:
            return f"{self.last_intent} {self.last_target}"
        elif self.last_intent:
            return self.last_intent
        return None
    
    def get_context_for_llm(self) -> str:
        """
        Get formatted context string for LLM prompt.
        
        Returns recent conversation history as a string.
        """
        if not self.messages:
            return "No previous conversation."
        
        lines = []
        for msg in self.messages[-5:]:  # Last 5 messages
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"{role}: {msg.content}")
        
        context = "\n".join(lines)
        
        if self.pending_clarification:
            context += f"\n[Waiting for clarification about: {self.pending_clarification}]"
        
        if self.last_intent:
            context += f"\n[Last action: {self.last_intent} {self.last_target or ''}]"
        
        return context
    
    def get_message_history(self) -> List[Dict[str, str]]:
        """Get message history in OpenAI-compatible format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.messages
        ]
    
    def reset(self):
        """Clear conversation state."""
        self.messages = []
        self.pending_clarification = None
        self.last_intent = None
        self.last_target = None
        self.last_action_success = None
        self.updated_at = datetime.now()
    
    def _trim_history(self):
        """Keep only the last MAX_HISTORY messages."""
        if len(self.messages) > self.MAX_HISTORY:
            self.messages = self.messages[-self.MAX_HISTORY:]


# Session storage
_contexts: Dict[str, ConversationContext] = {}


def get_context(session_id: str) -> ConversationContext:
    """Get or create a conversation context for a session."""
    if session_id not in _contexts:
        _contexts[session_id] = ConversationContext(session_id)
    return _contexts[session_id]


def clear_context(session_id: str):
    """Clear a session's conversation context."""
    if session_id in _contexts:
        _contexts[session_id].reset()
