"""
Conversational Brain V2 - LLM-First Architecture with Continuous Memory Flow.

The brain now works like ChatGPT:
1. LLM decides intent + mode (CHAT / ASK / ACT) FIRST
2. Patterns ONLY for hard overrides (stop, safety)
3. Confidence gate for ACT decisions
4. REAL MEMORY INTEGRATION - continuous flow of episodic memory

This is the shift from "regex brain with LLM backup" to "LLM brain with rule reflexes + memory".
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
import json
import asyncio

# Memory integration
from app.memory.context import get_session, get_context_for_llm, update_session
from app.db.episodic_memory_repo import TimelineEvent, log_event, get_timeline, search_memories, get_memory_summary
from app.db.firebase_client import get_firestore_client

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Startup check for GROQ
_groq_key = os.getenv("GROQ_API_KEY", "")
if _groq_key:
    logger.info(f"[BRAIN] GROQ_API_KEY loaded ({len(_groq_key)} chars)")
else:
    logger.warning(f"[BRAIN] GROQ_API_KEY not found! Looked in: {env_path}")


# =============================================================================
# Output Schema
# =============================================================================

class BrainOutputType(str, Enum):
    CHAT = "CHAT"  # Natural conversation response
    ASK = "ASK"    # Follow-up question needed
    ACT = "ACT"    # Execute automation


class BrainOutput(BaseModel):
    """Enhanced structured output from the brain."""
    type: BrainOutputType
    message: Optional[str] = None      # Response for CHAT/ASK
    question: Optional[str] = None     # Question for ASK
    intent: Optional[str] = None       # Action intent for ACT
    target: Optional[str] = None       # Action target for ACT
    confidence: float = 0.0            # Confidence for ACT
    reasoning: Optional[str] = None    # Why this decision
    
    # Enhanced fields
    mood: Optional[str] = None         # Detected user mood
    memories_used: List[str] = []      # Memory references used
    suggestions: List[str] = []        # Proactive suggestions
    personalization: Dict[str, Any] = {}  # User-specific adaptations


# =============================================================================
# Hard Override Patterns (ONLY for safety/interrupts)
# =============================================================================

import re

STOP_PATTERNS = [
    r"^stop\b", r"^cancel\b", r"^abort\b", r"^quit\b",
    r"^nevermind\b", r"^never\s+mind\b", r"^forget\s+it\b",
]

EMERGENCY_STOP = "Okay, I've stopped. What would you like me to do instead?"


# =============================================================================
# Conversation Context Class
# =============================================================================

class ConversationContext:
    """Enhanced conversation context with memory."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.user_mood: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.last_target: Optional[str] = None
        self.conversation_start = datetime.now()
        self.topics_discussed: List[str] = []
        self.user_preferences: Dict[str, Any] = {}
        
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        # Keep last 20 messages
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]
            
    def add_user_message(self, content: str):
        self.add_message("user", content)
        
    def add_assistant_message(self, content: str):
        self.add_message("assistant", content)
        
    def get_context_for_llm(self) -> str:
        if not self.messages:
            return "No conversation history"
        
        topics = self.topics_discussed[-3:]  # Last 3 topics
        mood_desc = f" (mood: {self.user_mood})" if self.user_mood else ""
        duration = (datetime.now() - self.conversation_start).total_seconds() / 60
        
        return f"Chat ongoing for {duration:.1f}min{mood_desc}. Recent topics: {', '.join(topics)}"


# =============================================================================
# Groq LLM Configuration (for natural conversation)
# =============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# =============================================================================
# Enhanced System Prompt with Memory Integration
# =============================================================================

BRAIN_SYSTEM_PROMPT = """
You are Kernel, an advanced AI assistant designed as the intelligent core of your PC.

## Identity:
- Name: Kernel
- Purpose: PC Automation Assistant with continuous memory
- Personality: Efficient, proactive, context-aware, and reliable

## Core Capabilities:
- Natural conversation with personality
- Memory of past interactions and user preferences
- Emotional awareness and adaptive responses
- Contextual understanding of user's current situation
- Proactive assistance and suggestions

## Automation vs Conversation Detection:
IMPORTANT: Distinguish between conversation and automation requests:
- CONVERSATION: greetings, questions, casual chat ("hi", "how are you", "what's up")
- AUTOMATION: commands to perform tasks ("clean downloads", "open notepad", "organize files")

## Memory Integration:
You have access to:
1. **Episodic Memory**: Past conversations and actions
2. **Session Context**: Current session state and recent actions
3. **User Preferences**: Learned patterns and settings
4. **Conversation History**: This chat's context

## Response Guidelines:
- Be efficient, direct, and helpful (Kernel's personality)
- Reference past interactions when relevant using memory
- Adapt tone based on detected mood
- Suggest next steps when appropriate
- Learn and remember user preferences
- Be proactive but not intrusive
- Sign responses as "Kernel" when appropriate

## Kernel's Voice Style:
- Efficient: Get straight to the point
- Proactive: Anticipate user needs
- Context-aware: Use memory to personalize
- Reliable: Execute tasks precisely

OUTPUT FORMAT (JSON only):
{
  "mode": "CHAT" | "ASK" | "ACT",
  "reply": "your response message",
  "intent": "action type if ACT (open_app, navigate, type, etc.)",
  "target": "action target if ACT (chrome, youtube.com, etc.)",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

RULES:
- CHAT → reply is your response, no intent/target needed
- ASK → reply is a clarifying question
- ACT → intent + target required, confidence required

AUTOMATION TRIGGERS:
If message contains ANY of these, prioritize ACT mode:
- Action verbs: "open", "close", "start", "launch", "run", "execute", "do", "scan", "clean", "organize", "move", "delete", "rename"
- File/folder names: "downloads", "desktop", "documents", "pictures", "videos", "music"
- App names: "notepad", "chrome", "explorer", "calculator", "word", "excel"
- System commands: "shutdown", "restart", "lock", "sleep"

EXAMPLES:
User: "hi" → CHAT (greeting)
User: "clean downloads" → ACT (automation)
User: "organize my files" → ACT (automation)
User: "open chrome" → ACT (automation)
User: "how are you?" → CHAT (status check)
User: "what's up?" → CHAT (casual chat)
User: "tell me a joke" → CHAT (entertainment)

Be natural. Be helpful. Be like ChatGPT."""


# =============================================================================
# LLM-First Brain with Continuous Memory Flow
# =============================================================================

class ConversationalBrain:
    """
    LLM-First Conversational Brain with Real Memory Integration.
    
    The LLM decides EVERYTHING. Patterns only guard/override.
    Memory flows continuously from episodic storage.
    """
    
    def __init__(self):
        self._conversation_summary = ""
    
    async def process(
        self, 
        message: str, 
        context: "ConversationContext" = None,
        session_id: str = "default"
    ) -> BrainOutput:
        """
        Process a user message using LLM-first approach with continuous memory flow.
        """
        message = message.strip()
        message_lower = message.lower()
        
        logger.info(f"[BRAIN] Processing: '{message}'")
        
        # ===========================================
        # STEP 1: Automation vs Conversation Detection
        # ===========================================
        
        # Check for automation triggers first
        if self._is_automation_request(message_lower):
            logger.info(f"[BRAIN] Automation request detected: '{message}'")
            # Force ACT mode for automation requests
            return await self._process_as_automation(message, context, session_id)
        
        # ===========================================
        # STEP 1. Hard Overrides (Safety Reflexes)
        # ===========================================
        
        # STOP/CANCEL - immediate interrupt
        if self._matches_any(message_lower, STOP_PATTERNS):
            logger.info(f"[BRAIN] → CHAT (hard override: stop)")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=EMERGENCY_STOP,
                reasoning="Stop command detected (hard override)"
            )
        
        # ===========================================
        # STEP 2: LLM Decides Everything Else with Memory
        # ===========================================
        
        llm_output = await self._llm_decide_with_memory(message, context, session_id)
        
        # ===========================================
        # STEP 3: Post-LLM Guards (Confidence Gate)
        # ===========================================
        
        if llm_output.type == BrainOutputType.ACT:
            if llm_output.confidence < 0.7:
                # Low confidence ACT → Force to ASK
                logger.info(f"[BRAIN] → ASK (confidence gate: {llm_output.confidence:.0%})")
                return BrainOutput(
                    type=BrainOutputType.ASK,
                    message=f"Just to confirm - did you want me to {llm_output.intent} {llm_output.target or ''}?",
                    question=f"Did you want me to {llm_output.intent} {llm_output.target or ''}?",
                    intent=llm_output.intent,
                    target=llm_output.target,
                    confidence=llm_output.confidence,
                    reasoning=f"Confidence gate: {llm_output.confidence:.0%} < 70%"
                )
            
            # Store for "do that again"
            if context:
                context.last_intent = llm_output.intent
                context.last_target = llm_output.target
        
        return llm_output
    
    async def _llm_decide_with_memory(
        self, 
        message: str, 
        context: "ConversationContext",
        session_id: str = "default"
    ) -> BrainOutput:
        """
        Enhanced LLM decision with REAL continuous memory flow.
        """
        import httpx
        import json
        
        if not GROQ_API_KEY:
            logger.warning("[BRAIN] No GROQ_API_KEY - using Gemini fallback")
            return await self._gemini_fallback(message, context)
        
        try:
            # ===========================================
            # STEP 1: Gather REAL Memory & Context
            # ===========================================
            
            # Get session context
            session_context = get_session(session_id)
            context_data = get_context_for_llm(session_id)
            
            # Get REAL recent memories from episodic storage
            recent_memories = await self._get_continuous_memories(session_id)
            
            # Search for relevant memories based on current message
            relevant_memories = await self._search_relevant_memories(session_id, message)
            
            # Detect mood from message
            detected_mood = self._detect_mood(message)
            if context:
                context.user_mood = detected_mood
            
            # ===========================================
            # STEP 2: Build Enhanced Prompt with REAL Memory
            # ===========================================
            
            messages = [{"role": "system", "content": BRAIN_SYSTEM_PROMPT}]
            
            # Add REAL memory context
            if recent_memories:
                # Deduplicate and preserve chronological order (newest first)
                seen = set()
                unique_memories = []
                for mem in reversed(recent_memories[-5:]):  # newest first
                    if mem not in seen:
                        seen.add(mem)
                        unique_memories.append(mem)
                memory_context = "\n".join([f"- {mem}" for mem in reversed(unique_memories)])  # restore chronological
                messages.append({
                    "role": "system", 
                    "content": f"Recent memories from continuous flow (chronological, newest last):\n{memory_context}"
                })
                logger.info(f"[BRAIN] Added {len(unique_memories)} real memories to context")
            
            # Add RELEVANT searched memories for specific queries
            if relevant_memories:
                # Deduplicate relevant memories
                seen = set()
                unique_relevant = []
                for mem in relevant_memories:
                    if mem not in seen:
                        seen.add(mem)
                        unique_relevant.append(mem)
                relevant_context = "\n".join([f"- {mem}" for mem in unique_relevant])
                messages.append({
                    "role": "system",
                    "content": f"Relevant memories for this query (deduplicated):\n{relevant_context}"
                })
                logger.info(f"[BRAIN] Added {len(unique_relevant)} relevant memories for query")
            
            # Add session context
            if context_data.get("last_command") or context_data.get("active_app"):
                session_summary = session_context.get_context_summary()
                messages.append({
                    "role": "system",
                    "content": f"Current context: {session_summary}"
                })
            
            # Add conversation history
            if context and context.messages:
                for msg in context.messages[-8:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    messages.append({"role": role, "content": content})
            
            # Add current message with mood
            mood_context = f" (mood: {detected_mood})" if detected_mood else ""
            messages.append({
                "role": "user", 
                "content": f"{message}{mood_context}"
            })
            
            # ===========================================
            # STEP 3: Call LLM with Memory Context
            # ===========================================
            
            logger.info(f"[BRAIN] Calling Groq with REAL memory context...")
            
            from groq import AsyncGroq
            client = AsyncGroq(api_key=GROQ_API_KEY)
            
            completion = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            reply_text = completion.choices[0].message.content.strip()
            logger.info(f"[BRAIN] Groq response: {reply_text[:200]}...")
            
            # ===========================================
            # STEP 4: Parse and Enhance Response
            # ===========================================
            
            try:
                result = json.loads(reply_text)
                brain_output = self._parse_llm_response(result)
                
                # Add enhanced features with REAL memory
                brain_output.mood = detected_mood
                brain_output.memories_used = [mem[:50] for mem in recent_memories[:3]]  # First 3 memories
                brain_output.suggestions = self._generate_suggestions(message, context, recent_memories)
                brain_output.personalization = self._get_personalization(session_context)
                
                # Log conversation to memory for CONTINUOUS FLOW
                await self._log_to_continuous_memory(session_id, message, brain_output)
                
                return brain_output
                
            except json.JSONDecodeError:
                logger.warning(f"[BRAIN] Failed to parse JSON, treating as chat")
                return BrainOutput(
                    type=BrainOutputType.CHAT,
                    message=reply_text,
                    mood=detected_mood,
                    reasoning="LLM response (non-JSON)"
                )
                    
        except Exception as e:
            logger.error(f"[BRAIN] Groq request failed: {e}")
            return await self._gemini_fallback(message, context)
    
    async def _get_continuous_memories(self, session_id: str, limit: int = 10) -> List[str]:
        """
        Get REAL memories from episodic storage for continuous flow.
        """
        try:
            # Get ACTUAL timeline events from episodic memory
            events = await get_timeline(session_id, limit)
            memories = []
            
            logger.info(f"[BRAIN] DEBUG: Session {session_id} retrieved {len(events)} events")
            for i, event in enumerate(events[:3]):  # Log first 3 events
                logger.info(f"[BRAIN] DEBUG: Event {i+1}: {event['type']} - {event['content'][:50]}...")
            
            for event in events:
                # Format memory entries based on event type
                if event['type'] == 'chat_user':
                    memories.append(f"User said: {event['content']}")
                elif event['type'] == 'chat_agent':
                    memories.append(f"Assistant responded: {event['content']}")
                elif event['type'] == 'action_tool':
                    memories.append(f"Action performed: {event['content']}")
                elif event['type'] == 'memory_thought':
                    memories.append(f"Thought: {event['content']}")
                else:
                    memories.append(f"Event: {event['content']}")
            
            logger.info(f"[BRAIN] Retrieved {len(memories)} REAL memories from continuous storage")
            return memories[:limit]
            
        except Exception as e:
            logger.warning(f"[BRAIN] Failed to get continuous memories: {e}")
            return []
    
    async def _log_to_continuous_memory(self, session_id: str, user_message: str, brain_output: BrainOutput):
        """
        Log conversation to episodic memory for CONTINUOUS FLOW.
        """
        try:
            # Log user message
            await log_event(
                user_id=session_id,
                event_type="chat_user",
                content=user_message,
                metadata={"mood": brain_output.mood}
            )
            
            # Log agent response
            await log_event(
                user_id=session_id,
                event_type="chat_agent",
                content=brain_output.message or "",
                metadata={
                    "type": brain_output.type.value,
                    "confidence": brain_output.confidence,
                    "memories_used": len(brain_output.memories_used)
                }
            )
            
            logger.info(f"[BRAIN] Logged conversation to continuous memory flow")
            
        except Exception as e:
            logger.warning(f"[BRAIN] Failed to log to continuous memory: {e}")
    
    async def _search_relevant_memories(self, session_id: str, message: str) -> List[str]:
        """
        Search for relevant memories based on the current message.
        This enhances context by finding specific past interactions.
        """
        try:
            relevant_memories = []

            results = await search_memories(
                user_id=session_id,
                query=message,
                event_types=["action_tool", "chat_user", "chat_agent"],
                limit=6
            )

            for result in results:
                content = result.get("content", "")
                event_type = result.get("type", "")

                if event_type == "action_tool":
                    relevant_memories.append(f"Previous action: {content}")
                elif event_type == "chat_user":
                    relevant_memories.append(f"You previously said: {content}")
                elif event_type == "chat_agent":
                    relevant_memories.append(f"I previously responded: {content}")

            logger.info(f"[BRAIN] Found {len(relevant_memories)} relevant memories for '{message}'")
            return relevant_memories[:3]

        except Exception as e:
            logger.warning(f"[BRAIN] Failed to search relevant memories: {e}")
            return []
    
    def _parse_llm_response(self, result: Dict[str, Any]) -> BrainOutput:
        """Parse structured LLM response into BrainOutput."""
        mode = result.get("mode", "CHAT").upper()
        reply = result.get("reply", "")
        intent = result.get("intent")
        target = result.get("target")
        confidence = float(result.get("confidence", 0))
        reason = result.get("reason", "")
        
        if mode == "ACT":
            logger.info(f"[BRAIN] → ACT: {intent} {target} ({confidence:.0%})")
            return BrainOutput(
                type=BrainOutputType.ACT,
                message=reply,
                intent=intent,
                target=target,
                confidence=confidence,
                reasoning=reason
            )
        elif mode == "ASK":
            logger.info(f"[BRAIN] → ASK: {reply[:50]}... ({confidence:.0%})")
            return BrainOutput(
                type=BrainOutputType.ASK,
                message=reply,
                question=reply,
                reasoning=reason
            )
        else:  # CHAT
            logger.info(f"[BRAIN] → CHAT: {reply[:50]}")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message=reply,
                reasoning=reason
            )
    
    async def _gemini_fallback(
        self, 
        message: str, 
        context: "ConversationContext"
    ) -> BrainOutput:
        """Fallback to Gemini if Groq unavailable."""
        try:
            from app.reasoning.intent_analyzer import analyze_command
            
            context_str = ""
            if context:
                context_str = f"Recent conversation: {context.get_context_for_lll()}"
            
            analysis = await analyze_command(message, {"context": context_str})
            
            intent = analysis.get("intent", "unclear")
            confidence = analysis.get("confidence", 0.0)
            actions = analysis.get("actions", [])
            
            logger.info(f"[BRAIN] Gemini fallback: intent={intent}, confidence={confidence}")
            
            if confidence >= 0.7 and actions:
                first_action = actions[0]
                return BrainOutput(
                    type=BrainOutputType.ACT,
                    message=f"Got it, {intent}!",
                    intent=intent,
                    target=first_action.get("target", first_action.get("content", "")),
                    confidence=confidence,
                    reasoning="Gemini fallback with high confidence"
                )
            elif confidence >= 0.4:
                return BrainOutput(
                    type=BrainOutputType.ASK,
                    message=f"I think you want to {intent}. Is that right?",
                    question=f"Did you want me to {intent}?",
                    intent=intent,
                    confidence=confidence,
                    reasoning="Gemini fallback with medium confidence"
                )
            else:
                return BrainOutput(
                    type=BrainOutputType.CHAT,
                    message="I'd love to help! Could you tell me more about what you'd like me to do?",
                    reasoning="Gemini fallback with low confidence"
                )
                
        except Exception as e:
            logger.error(f"[BRAIN] Gemini fallback failed: {e}")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message="I'm having trouble understanding that. Could you try rephrasing?",
                reasoning=f"All fallbacks failed: {e}"
            )
    
    def _is_automation_request(self, message: str) -> bool:
        """Check if message contains automation triggers."""
        automation_triggers = [
            # Action verbs
            "open", "close", "start", "launch", "run", "execute", "do", "scan", "clean", "organize", "move", "delete", "rename",
            # File/folder names
            "downloads", "desktop", "documents", "pictures", "videos", "music", "temp", "cache",
            # App names
            "notepad", "chrome", "explorer", "calculator", "word", "excel", "powerpoint", "vscode", "code",
            # System commands
            "shutdown", "restart", "lock", "sleep"
        ]
        
        return any(trigger in message for trigger in automation_triggers)
    
    async def _process_as_automation(
        self, 
        message: str, 
        context: "ConversationContext",
        session_id: str
    ) -> BrainOutput:
        """Process message as automation request."""
        try:
            # Use LLM to determine the automation action
            llm_output = await self._llm_decide_with_memory(message, context, session_id)
            
            # Ensure ACT mode for automation
            if llm_output.type != BrainOutputType.ACT:
                # Force ACT mode for automation requests
                logger.info(f"[BRAIN] Forcing ACT mode for automation request")
                llm_output.type = BrainOutputType.ACT
                llm_output.confidence = 0.8  # Set reasonable confidence
            
            return llm_output
            
        except Exception as e:
            logger.error(f"[BRAIN] Error processing automation: {e}")
            return BrainOutput(
                type=BrainOutputType.CHAT,
                message="I had trouble processing that automation request. Could you try rephrasing?",
                reasoning=f"Error: {str(e)}"
            )
    
    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        for pattern in patterns:
            if pattern in text:
                return True
        return False

    # ===========================================
    # ENHANCED FEATURE METHODS
    # ===========================================
    
    def _detect_mood(self, message: str) -> Optional[str]:
        """Detect user mood from message."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["thanks", "thank you", "awesome", "great"]):
            return "happy"
        elif any(word in message_lower for word in ["help", "stuck", "confused", "problem"]):
            return "need_help"
        elif any(word in message_lower for word in ["bored", "nothing", "chilling"]):
            return "casual"
        elif any(word in message_lower for word in ["busy", "hurry", "quick"]):
            return "urgent"
        
        return None
    
    def _generate_suggestions(self, message: str, context: Any, memories: List[str]) -> List[str]:
        """Generate proactive suggestions based on context and memory patterns."""
        suggestions = []
        
        # Context-aware suggestions
        if "open" in message.lower():
            suggestions.extend(["open browser", "open notepad", "open calculator"])
        
        if "help" in message.lower():
            suggestions.extend(["show me what you can do", "tell me about features"])
        
        if context and hasattr(context, 'last_command') and context.last_command:
            suggestions.append("do that again")
        
        # Memory-based suggestions
        memory_text = " ".join(memories).lower()
        if "chrome" in memory_text and "open" in message.lower():
            suggestions.append("open chrome again")
        if "notepad" in memory_text:
            suggestions.append("open notepad")
        
        return suggestions[:3]
    
    def _get_personalization(self, session_context) -> Dict[str, Any]:
        """Get user personalization data."""
        return {
            "preferred_browser": session_context.preferences.get("default_browser", "chrome"),
            "conversation_style": "friendly",
            "proactive_suggestions": True
        }


# =============================================================================
# Singleton & Entry Point
# =============================================================================

_brain: Optional[ConversationalBrain] = None


def get_brain() -> ConversationalBrain:
    """Get the singleton brain instance."""
    global _brain
    if _brain is None:
        _brain = ConversationalBrain()
    return _brain


async def process_message(
    message: str, 
    session_id: str = "default"
) -> BrainOutput:
    """
    Main entry point for processing user messages with continuous memory flow.
    LLM-first, patterns-as-guards.
    """
    brain = get_brain()
    
    # Create or get context
    context = get_context(session_id)
    context.add_user_message(message)
    
    # Process through LLM-first brain with REAL memory
    output = await brain.process(message, context, session_id)
    
    # Add response to context
    if output.type in (BrainOutputType.CHAT, BrainOutputType.ASK):
        response_text = output.message or output.question or ""
        context.add_assistant_message(response_text)
    
    return output


def get_context(session_id: str) -> ConversationContext:
    """Get or create conversation context."""
    return ConversationContext(session_id)
