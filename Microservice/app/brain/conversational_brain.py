"""
Conversational Brain V2 - LLM-First Architecture.

The brain now works like ChatGPT:
1. LLM decides intent + mode (CHAT / ASK / ACT) FIRST
2. Patterns ONLY for hard overrides (stop, safety)
3. Confidence gate for ACT decisions

This is the shift from "regex brain with LLM backup" to "LLM brain with rule reflexes".
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum
from pathlib import Path

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Startup check for GROQ
_groq_key = os.getenv("GROQ_API_KEY", "")
if _groq_key:
    logger.info(f"[BRAIN] ✅ GROQ_API_KEY loaded ({len(_groq_key)} chars)")
else:
    logger.warning(f"[BRAIN] ⚠️ GROQ_API_KEY not found! Looked in: {env_path}")


# =============================================================================
# Output Schema
# =============================================================================

class BrainOutputType(str, Enum):
    CHAT = "CHAT"  # Natural conversation response
    ASK = "ASK"    # Follow-up question needed
    ACT = "ACT"    # Execute automation


class BrainOutput(BaseModel):
    """Structured output from the brain."""
    type: BrainOutputType
    message: Optional[str] = None      # Response for CHAT/ASK
    question: Optional[str] = None     # Question for ASK
    intent: Optional[str] = None       # Action intent for ACT
    target: Optional[str] = None       # Action target for ACT
    confidence: float = 0.0            # Confidence for ACT
    reasoning: Optional[str] = None    # Why this decision


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
# Groq LLM Configuration (for natural conversation)
# =============================================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# =============================================================================
# LLM System Prompt (The Core of Natural Behavior)
# =============================================================================

BRAIN_SYSTEM_PROMPT = """You are Kernel, a conversational AI assistant with desktop automation abilities.

You can:
- Chat naturally about any topic
- Ask follow-up questions when unclear
- Decide when to execute computer actions

You must:
- Behave like ChatGPT in conversation
- Only request automation when user intent is CLEAR
- Ask questions when unsure or command is incomplete
- Be concise (1-3 sentences unless asked for more)

You must NEVER execute actions yourself.
You ONLY decide whether an action should happen.

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

EXAMPLES:
User: "hi"
{"mode":"CHAT","reply":"Hey! How can I help you today?","confidence":0,"reason":"greeting"}

User: "what is evaporation?"  
{"mode":"CHAT","reply":"Evaporation is the process where liquid turns into vapor at the surface, even below boiling point. It's how puddles disappear on a sunny day!","confidence":0,"reason":"knowledge question"}

User: "how are you?"
{"mode":"CHAT","reply":"I'm doing great, thanks for asking! Ready to help whenever you need.","confidence":0,"reason":"casual conversation"}

User: "open"
{"mode":"ASK","reply":"What would you like me to open?","confidence":0.3,"reason":"incomplete command"}

User: "open chrome"
{"mode":"ACT","reply":"Opening Chrome for you!","intent":"open_app","target":"chrome","confidence":0.95,"reason":"clear action request"}

User: "go to youtube"
{"mode":"ACT","reply":"Navigating to YouTube!","intent":"navigate","target":"youtube.com","confidence":0.9,"reason":"clear navigation request"}

User: "actually no"
{"mode":"CHAT","reply":"No problem! What would you like me to do instead?","confidence":0,"reason":"cancellation"}

User: "tell me a joke"
{"mode":"CHAT","reply":"Why don't scientists trust atoms? Because they make up everything! 😄","confidence":0,"reason":"entertainment request"}

User: "nothing just chilling"
{"mode":"CHAT","reply":"Nice! I'm here whenever you need me. Feel free to chat or ask me to do something.","confidence":0,"reason":"casual"}

Be natural. Be helpful. Be like ChatGPT."""


# =============================================================================
# LLM-First Brain
# =============================================================================

class ConversationalBrain:
    """
    LLM-First Conversational Brain.
    
    The LLM decides EVERYTHING. Patterns only guard/override.
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
        Process a user message using LLM-first approach.
        """
        message = message.strip()
        message_lower = message.lower()
        
        logger.info(f"[BRAIN] Processing: '{message}'")
        
        # ===========================================
        # STEP 1: Hard Overrides (Safety Reflexes)
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
        # STEP 2: LLM Decides Everything Else
        # ===========================================
        
        llm_output = await self._llm_decide(message, context)
        
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
    
    async def _llm_decide(
        self, 
        message: str, 
        context: "ConversationContext"
    ) -> BrainOutput:
        """
        Use LLM to decide mode and generate response.
        This is the PRIMARY decision maker.
        """
        import httpx
        import json
        
        if not GROQ_API_KEY:
            logger.warning("[BRAIN] No GROQ_API_KEY - using Gemini fallback")
            return await self._gemini_fallback(message, context)
        
        try:
            # Build conversation history
            messages = [{"role": "system", "content": BRAIN_SYSTEM_PROMPT}]
            
            # Add context summary if available
            if context and context.messages:
                for msg in context.messages[-10:]:
                    # Handle Pydantic model access
                    role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                    content = msg.content
                    
                    messages.append({
                        "role": role,
                        "content": content
                    })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Call Groq
            logger.info(f"[BRAIN] Calling Groq LLM (via SDK)...")
            
            # Lazy import Groq to avoid circular deps
            from groq import AsyncGroq
            client = AsyncGroq(api_key=GROQ_API_KEY)
            
            completion = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            reply_text = completion.choices[0].message.content.strip()
            logger.info(f"[BRAIN] Groq raw: {reply_text[:200]}")
            
            # Parse JSON response
            try:
                result = json.loads(reply_text)
                return self._parse_llm_response(result)
            except json.JSONDecodeError:
                logger.warning(f"[BRAIN] Failed to parse JSON, treating as chat")
                return BrainOutput(
                    type=BrainOutputType.CHAT,
                    message=reply_text,
                    reasoning="LLM response (non-JSON)"
                )
                    
        except Exception as e:
            logger.error(f"[BRAIN] Groq request failed: {e}")
            return await self._gemini_fallback(message, context)
    
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
            logger.info(f"[BRAIN] → ASK: {reply[:50]}")
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
                context_str = f"Recent conversation: {context.get_context_for_llm()}"
            
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
    
    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


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
    Main entry point for processing user messages.
    LLM-first, patterns-as-guards.
    """
    from app.brain.conversation_context import get_context
    
    brain = get_brain()
    context = get_context(session_id)
    
    # Add user message to context
    context.add_user_message(message)
    
    # Process through LLM-first brain
    output = await brain.process(message, context, session_id)
    
    # Add response to context
    if output.type in (BrainOutputType.CHAT, BrainOutputType.ASK):
        response_text = output.message or output.question or ""
        context.add_assistant_message(response_text)
    
    return output
 