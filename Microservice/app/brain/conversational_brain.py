"""
Conversational Brain - Central Intelligence for CHAT/ASK/ACT routing.

This is the new entry point for all user messages. Instead of treating
every input as a command, the brain decides:

1. CHAT - Respond naturally (greetings, help, casual)
2. ASK  - Request clarification (unclear intent)
3. ACT  - Execute automation (confident intent)

This enables natural conversation while maintaining automation capability.
"""

import os
import re
import logging
from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Output Schema (Strict)
# =============================================================================

class BrainOutputType(str, Enum):
    CHAT = "CHAT"  # Natural conversation response
    ASK = "ASK"    # Follow-up question needed
    ACT = "ACT"    # Execute automation


class BrainOutput(BaseModel):
    """
    Strict output format for the Conversational Brain.
    
    The brain MUST output one of three types:
    - CHAT: Pure conversation, no automation
    - ASK: Need more information before acting
    - ACT: Ready to execute with high confidence
    """
    type: BrainOutputType
    message: Optional[str] = None      # Response for CHAT
    question: Optional[str] = None     # Question for ASK
    intent: Optional[str] = None       # Action intent for ACT
    target: Optional[str] = None       # Action target for ACT
    confidence: float = 0.0            # Confidence for ACT (safety gate)
    reasoning: Optional[str] = None    # Why this decision was made


# =============================================================================
# Pattern Matchers (Fast Path before LLM)
# =============================================================================

GREETING_PATTERNS = [
    r"^hi\b", r"^hello\b", r"^hey\b", r"^howdy\b", r"^greetings\b",
    r"^good\s*(morning|afternoon|evening|day)\b",
    r"^what'?s?\s*up\b", r"^sup\b", r"^yo\b",
]

HELP_PATTERNS = [
    r"^help\b", r"what\s+can\s+you\s+do",
    r"what\s+are\s+you(r)?\s+capabilit",
    r"^how\s+do\s+(i|you)", r"^show\s+me\s+what",
    r"^what\s+commands", r"^list\s+(your\s+)?commands",
]

THANKS_PATTERNS = [
    r"^thanks?\b", r"^thank\s+you\b", r"^ty\b", r"^thx\b",
    r"^appreciate", r"^cheers\b",
]

FAREWELL_PATTERNS = [
    r"^bye\b", r"^goodbye\b", r"^see\s+you\b", r"^later\b",
    r"^good\s*night\b", r"^take\s+care\b",
]

STOP_PATTERNS = [
    r"^stop\b", r"^cancel\b", r"^abort\b", r"^nevermind\b",
    r"^never\s+mind\b", r"^forget\s+it\b", r"^wait\b",
]

REPEAT_PATTERNS = [
    r"^again\b", r"^repeat\b", r"do\s+(that|it)\s+again",
    r"^same\s+(thing|action)\b", r"^one\s+more\s+time\b",
]

# Incomplete action patterns (need clarification)
INCOMPLETE_PATTERNS = [
    (r"^open\s*$", "What would you like me to open?", "open"),
    (r"^close\s*$", "What would you like me to close?", "close"),
    (r"^type\s*$", "What would you like me to type?", "type"),
    (r"^search\s*$", "What would you like me to search for?", "search"),
    (r"^go\s+to\s*$", "Where would you like me to go?", "navigate"),
    (r"^play\s*$", "What would you like me to play?", "play"),
    (r"^run\s*$", "What would you like me to run?", "run"),
    (r"^click\s*$", "What should I click on?", "click"),
]


# =============================================================================
# Greeting Responses (Varied)
# =============================================================================

GREETING_RESPONSES = [
    "Hello! How can I help you today?",
    "Hey there! What would you like me to do?",
    "Hi! Ready to assist. What's on your mind?",
    "Greetings! I'm here to help.",
    "Hello! What can I do for you?",
]

HELP_RESPONSE = """I can help you with:

**🖥️ Apps & Windows**
• Open apps: "open chrome", "launch notepad"
• Close apps: "close spotify"

**⌨️ Typing & Input**
• Type text: "type hello world"
• Press keys: "press enter", "press ctrl+s"

**🌐 Browser**
• Navigate: "go to youtube.com"
• Search: "search for python tutorials"

**🎵 Media**
• Play/pause, volume, next/previous

**📁 Files (Janitor)**
• Organize files, clean downloads

Just tell me what you need!"""

THANKS_RESPONSES = [
    "You're welcome! Let me know if you need anything else.",
    "Happy to help! Anything else?",
    "No problem! I'm here if you need me.",
]

FAREWELL_RESPONSES = [
    "Goodbye! Take care!",
    "See you later!",
    "Bye! Have a great day!",
]

STOP_RESPONSE = "Okay, I've stopped. Let me know when you're ready."


# =============================================================================
# Conversational Brain
# =============================================================================

class ConversationalBrain:
    """
    Central intelligence that decides: CHAT, ASK, or ACT.
    
    Conversation first, execution second.
    """
    
    def __init__(self):
        self._response_index = 0  # For varied responses
    
    async def process(
        self, 
        message: str, 
        context: "ConversationContext" = None,
        session_id: str = "default"
    ) -> BrainOutput:
        """
        Process a user message and decide the response type.
        
        Args:
            message: User's input
            context: Conversation context for multi-turn
            session_id: Session identifier
            
        Returns:
            BrainOutput with type CHAT, ASK, or ACT
        """
        message = message.strip()
        message_lower = message.lower()
        
        logger.info(f"[BRAIN] Processing: '{message}'")
        
        # === FAST PATH: Pattern matching for common cases ===
        
        # 1. Check for greetings
        if self._matches_any(message_lower, GREETING_PATTERNS):
            response = self._get_varied_response(GREETING_RESPONSES)
            logger.info(f"[BRAIN] → CHAT (greeting)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=response,
                reasoning="Greeting detected"
            )
        
        # 2. Check for help queries
        if self._matches_any(message_lower, HELP_PATTERNS):
            logger.info(f"[BRAIN] → CHAT (help)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=HELP_RESPONSE,
                reasoning="Help query detected"
            )
        
        # 3. Check for thanks
        if self._matches_any(message_lower, THANKS_PATTERNS):
            response = self._get_varied_response(THANKS_RESPONSES)
            logger.info(f"[BRAIN] → CHAT (thanks)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=response,
                reasoning="Thanks detected"
            )
        
        # 4. Check for farewell
        if self._matches_any(message_lower, FAREWELL_PATTERNS):
            response = self._get_varied_response(FAREWELL_RESPONSES)
            logger.info(f"[BRAIN] → CHAT (farewell)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=response,
                reasoning="Farewell detected"
            )
        
        # 5. Check for stop/cancel
        if self._matches_any(message_lower, STOP_PATTERNS):
            logger.info(f"[BRAIN] → CHAT (stop)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=STOP_RESPONSE,
                reasoning="Stop command detected"
            )
        
        # 6. Check for repeat ("do that again")
        if self._matches_any(message_lower, REPEAT_PATTERNS):
            if context and context.get_last_action_description():
                last_action = context.get_last_action_description()
                logger.info(f"[BRAIN] → ACT (repeat: {last_action})")
                return BrainOutput(
                    type=BrainOutputType.ACT,
                    intent=context.last_intent,
                    target=context.last_target,
                    confidence=0.9,
                    reasoning=f"Repeating last action: {last_action}"
                )
            else:
                logger.info(f"[BRAIN] → ASK (nothing to repeat)")
                return BrainOutput(
                    type=BrainOutputType.ASK,
                    question="I don't have a previous action to repeat. What would you like me to do?",
                    reasoning="Repeat requested but no previous action"
                )
        
        # 7. Check for incomplete commands (need clarification)
        for pattern, question, intent in INCOMPLETE_PATTERNS:
            if re.match(pattern, message_lower, re.IGNORECASE):
                if context:
                    context.set_pending_clarification(question, intent)
                logger.info(f"[BRAIN] → ASK (incomplete: {intent})")
                return BrainOutput(
                    type=BrainOutputType.ASK,
                    question=question,
                    intent=intent,
                    reasoning=f"Incomplete command detected: {intent}"
                )
        
        # 8. Check if resolving a pending clarification
        if context and context.pending_clarification:
            combined = context.resolve_clarification(message)
            logger.info(f"[BRAIN] → ACT (clarification resolved: {combined})")
            return BrainOutput(
                type=BrainOutputType.ACT,
                intent=combined,
                target=message,
                confidence=0.85,
                reasoning=f"Clarification resolved: {combined}"
            )
        
        # === SLOW PATH: LLM analysis for complex cases ===
        return await self._analyze_with_llm(message, context, session_id)
    
    async def _analyze_with_llm(
        self, 
        message: str, 
        context: "ConversationContext",
        session_id: str
    ) -> BrainOutput:
        """
        Use LLM to analyze complex or ambiguous messages.
        """
        try:
            # Get context string
            context_str = context.get_context_for_llm() if context else "No context"
            
            # Use the intent analyzer for action detection
            from app.reasoning.intent_analyzer import analyze_command
            
            analysis = await analyze_command(message, {"context": context_str})
            
            intent = analysis.get("intent", "unclear")
            confidence = analysis.get("confidence", 0.0)
            actions = analysis.get("actions", [])
            
            logger.info(f"[BRAIN] LLM analysis: intent={intent}, confidence={confidence}, actions={len(actions)}")
            
            # High confidence with actions → ACT
            if confidence >= 0.7 and actions:
                first_action = actions[0]
                target = first_action.get("target", first_action.get("content", ""))
                
                logger.info(f"[BRAIN] → ACT (LLM confident)")
                return BrainOutput(
                    type=BrainOutputType.ACT,
                    intent=intent,
                    target=target,
                    confidence=confidence,
                    reasoning=analysis.get("reasoning", "LLM determined actionable intent")
                )
            
            # Low confidence but has actions → ASK for confirmation
            if 0.4 <= confidence < 0.7 and actions:
                first_action = actions[0]
                action_desc = f"{first_action.get('action', 'perform')} {first_action.get('target', first_action.get('content', ''))}"
                
                logger.info(f"[BRAIN] → ASK (low confidence)")
                return BrainOutput(
                    type=BrainOutputType.ASK,
                    question=f"Did you want me to {action_desc.strip()}?",
                    intent=intent,
                    confidence=confidence,
                    reasoning=f"Low confidence ({confidence:.0%}), asking for confirmation"
                )
            
            # Very low confidence or unclear → CHAT
            logger.info(f"[BRAIN] → CHAT (unclear intent)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=f"I'm not sure what you'd like me to do. Could you be more specific?\n\nSay 'help' to see what I can do!",
                reasoning=f"Intent unclear (confidence: {confidence:.0%})"
            )
            
        except Exception as e:
            logger.error(f"[BRAIN] LLM analysis failed: {e}")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message="I had trouble understanding that. Could you try rephrasing?",
                reasoning=f"LLM error: {str(e)}"
            )
    
    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _get_varied_response(self, responses: List[str]) -> str:
        """Get a varied response from a list (round-robin)."""
        response = responses[self._response_index % len(responses)]
        self._response_index += 1
        return response


# =============================================================================
# Singleton Instance
# =============================================================================

_brain: Optional[ConversationalBrain] = None


def get_brain() -> ConversationalBrain:
    """Get the singleton Conversational Brain instance."""
    global _brain
    if _brain is None:
        _brain = ConversationalBrain()
    return _brain


async def process_message(
    message: str, 
    session_id: str = "default"
) -> BrainOutput:
    """
    Main entry point for processing user messages.
    
    This is the function that WebSocket should call instead of
    going directly to the planner.
    """
    from app.brain.conversation_context import get_context
    
    brain = get_brain()
    context = get_context(session_id)
    
    # Add user message to context
    context.add_user_message(message)
    
    # Process through brain
    output = await brain.process(message, context, session_id)
    
    # Add assistant response to context (if CHAT or ASK)
    if output.type in (BrainOutputType.CHAT, BrainOutputType.ASK):
        response_text = output.message or output.question or ""
        context.add_assistant_message(response_text)
    
    return output
