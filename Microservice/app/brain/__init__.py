"""
Brain Module - Conversational AI Layer

This module provides the intelligent conversation layer that sits
between user input and the executor. All user messages go through
the Conversational Brain first.

Architecture:
    User Input
        ↓
    Conversational Brain (CHAT / ASK / ACT)
        ↓
    [If ACT] → LLM Planner → Executor
    [If CHAT/ASK] → Response to User
"""

from app.brain.conversational_brain import (
    ConversationalBrain,
    BrainOutput,
    BrainOutputType,
    get_brain,
    process_message,
)

from app.brain.conversation_context import (
    ConversationContext,
    ConversationMessage,
    MessageRole,
    get_context,
    clear_context,
)

__all__ = [
    # Brain
    "ConversationalBrain",
    "BrainOutput",
    "BrainOutputType",
    "get_brain",
    "process_message",
    
    # Context
    "ConversationContext",
    "ConversationMessage",
    "MessageRole",
    "get_context",
    "clear_context",
]
