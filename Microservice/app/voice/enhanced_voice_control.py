"""
Enhanced Voice Control System

Provides advanced voice interaction capabilities for the Kernal Agent system.
Supports multi-turn conversations, context retention, and proactive voice suggestions.

Features:
- Continuous voice recognition with wake word detection
- Multi-turn conversation support with context retention
- Natural language understanding with intent classification
- Proactive voice suggestions based on user behavior
- Voice command shortcuts and custom commands
- Emotional tone detection and response adaptation
- Multi-language support with automatic detection
"""

import logging
import asyncio
import json
import os
import re
from typing import Any, Optional, Dict, List, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


class VoiceCommand(Enum):
    """Predefined voice command types."""
    WAKE_UP = "wake_up"
    SLEEP = "sleep"
    EXECUTE_ACTION = "execute_action"
    QUERY = "query"
    CONTROL = "control"
    NAVIGATION = "navigation"
    DICTATION = "dictation"
    CUSTOM = "custom"


class ConversationState(Enum):
    """Current state of voice conversation."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    WAITING_CONFIRMATION = "waiting_confirmation"
    MULTI_TURN = "multi_turn"


class VoiceIntentType(Enum):
    """Types of voice intents."""
    COMMAND = "command"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    CORRECTION = "correction"
    FOLLOW_UP = "follow_up"


@dataclass
class VoiceIntent:
    """Represents a parsed voice intent."""
    intent_id: str
    intent_type: VoiceIntentType
    command: str
    entities: Dict[str, Any]
    confidence: float
    requires_confirmation: bool = False
    context_dependent: bool = False
    original_text: str = ""
    language: str = "en"
    emotional_tone: str = "neutral"


@dataclass
class ConversationContext:
    """Maintains conversation context across turns."""
    context_id: str
    user_id: str
    started_at: datetime
    last_interaction: datetime
    conversation_state: ConversationState
    intent_history: List[VoiceIntent]
    entities_memory: Dict[str, Any]
    pending_actions: List[Dict]
    user_preferences: Dict[str, Any]
    session_topic: Optional[str] = None


@dataclass
class VoiceResponse:
    """Represents a voice response to be spoken."""
    response_id: str
    text: str
    voice_settings: Dict[str, Any]
    requires_user_response: bool = False
    suggested_responses: List[str] = None
    emotional_tone: str = "neutral"
    priority: int = 1


class EnhancedVoiceControl:
    """Enhanced voice control system with advanced conversation capabilities."""
    
    def __init__(self):
        self.is_active = False
        self.wake_words = ["hey kernal", "ok kernal", "kernal agent"]
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.active_context_id: Optional[str] = None
        self.voice_shortcuts: Dict[str, str] = {}
        self.custom_commands: Dict[str, callable] = {}
        self.intent_patterns: Dict[str, List[str]] = {}
        self.response_templates: Dict[str, str] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.conversation_memory: List[Dict] = []
        self._setup_default_patterns()
        self._setup_response_templates()
        self._setup_voice_shortcuts()
    
    def _setup_default_patterns(self):
        """Setup default intent recognition patterns."""
        self.intent_patterns = {
            # Action commands
            "open_application": [
                r"open (?P<app_name>[\w\s]+)",
                r"launch (?P<app_name>[\w\s]+)",
                r"start (?P<app_name>[\w\s]+)"
            ],
            "close_application": [
                r"close (?P<app_name>[\w\s]+)",
                r"quit (?P<app_name>[\w\s]+)",
                r"exit (?P<app_name>[\w\s]+)"
            ],
            "click_element": [
                r"click (?P<target>[\w\s]+)",
                r"press (?P<target>[\w\s]+)",
                r"tap (?P<target>[\w\s]+)"
            ],
            "type_text": [
                r"type (?P<text>.+)",
                r"write (?P<text>.+)",
                r"enter (?P<text>.+)"
            ],
            "scroll_page": [
                r"scroll (?P<direction>up|down|left|right)",
                r"page (?P<direction>up|down)",
                r"move (?P<direction>up|down|left|right)"
            ],
            
            # Query commands
            "system_status": [
                r"how is (?P<system>system|computer|pc)",
                r"what's (?P<metric>cpu|memory|disk) usage",
                r"show (?P<info>performance|stats)"
            ],
            "weather_query": [
                r"what's the weather",
                r"how's the weather (?P<location>.*)?",
                r"weather (?P<location>.*)"
            ],
            "time_query": [
                r"what time is it",
                r"current time",
                r"what's the time"
            ],
            
            # Agent commands
            "agent_status": [
                r"how are my agents",
                r"agent status",
                r"what are agents doing"
            ],
            "run_agent": [
                r"run (?P<agent_name>[\w\s]+) agent",
                r"start (?P<agent_name>[\w\s]+) agent",
                r"activate (?P<agent_name>[\w\s]+)"
            ],
            "stop_agent": [
                r"stop (?P<agent_name>[\w\s]+) agent",
                r"deactivate (?P<agent_name>[\w\s]+)",
                r"pause (?P<agent_name>[\w\s]+)"
            ],
            
            # Control commands
            "volume_control": [
                r"(?P<action>set|change) volume to (?P<level>\d+)",
                r"volume (?P<direction>up|down)",
                r"(?P<action>mute|unmute)"
            ],
            "brightness_control": [
                r"(?P<action>set|change) brightness to (?P<level>\d+)",
                r"brightness (?P<direction>up|down)",
                r"make screen (?P<action>brighter|darker)"
            ],
            
            # Productivity commands
            "create_task": [
                r"create task (?P<task_description>.+)",
                r"add task (?P<task_description>.+)",
                r"remind me to (?P<task_description>.+)"
            ],
            "schedule_meeting": [
                r"schedule meeting (?P<meeting_details>.+)",
                r"book meeting (?P<meeting_details>.+)",
                r"set up meeting (?P<meeting_details>.+)"
            ],
            "take_break": [
                r"take (?P<break_type>short|long|coffee) break",
                r"start break",
                r"break time"
            ],
            
            # Security commands
            "security_scan": [
                r"scan for (?P<threat_type>viruses|malware|threats)",
                r"security scan",
                r"check security"
            ],
            "lock_screen": [
                r"lock (?P<target>screen|computer|pc)",
                r"lock my computer",
                r"secure screen"
            ],
            
            # Conversation control
            "repeat": [
                r"repeat (?P<what>that|last)",
                r"say again",
                r"what did you say"
            ],
            "clarify": [
                r"what do you mean",
                r"clarify (?P<what>.+)",
                r"explain (?P<what>.+)"
            ],
            "cancel": [
                r"cancel (?P<what>that|this|last command)",
                r"nevermind",
                r"forget it"
            ]
        }
    
    def _setup_response_templates(self):
        """Setup response templates for different situations."""
        self.response_templates = {
            # Confirmations
            "action_confirm": "I'll {action} for you. Should I proceed?",
            "action_complete": "Done! I've {action}.",
            "action_failed": "I couldn't {action}. {reason}",
            
            # Questions for clarification
            "need_clarification": "I need more information. {question}",
            "multiple_options": "I found several options: {options}. Which one?",
            "confirm_action": "Just to confirm, you want me to {action}?",
            
            # Status responses
            "listening": "I'm listening...",
            "processing": "Let me process that...",
            "ready": "I'm ready to help. What can I do for you?",
            
            # Error responses
            "not_understood": "I didn't quite catch that. Could you repeat?",
            "no_context": "I need more context. What would you like me to do?",
            "capability_limit": "I can't do that yet, but I can help with {alternatives}.",
            
            # Proactive suggestions
            "productivity_suggestion": "I noticed you've been working for a while. Would you like me to suggest a break?",
            "security_reminder": "It's been a while since your last security scan. Should I run one?",
            "maintenance_suggestion": "Your system could benefit from cleanup. Would you like me to organize your files?",
            
            # Conversation flow
            "follow_up": "Is there anything else I can help you with?",
            "context_switch": "I see you want to talk about something else. What can I help with?",
            "session_end": "Alright, I'll go back to monitoring. Just say my wake word when you need me."
        }
    
    def _setup_voice_shortcuts(self):
        """Setup voice shortcuts for common commands."""
        self.voice_shortcuts = {
            # Quick actions
            "screenshot": "take screenshot",
            "copy that": "copy selected text",
            "paste that": "paste clipboard",
            "save file": "save current document",
            "new file": "create new document",
            
            # Navigation shortcuts
            "go back": "navigate back",
            "go forward": "navigate forward",
            "go home": "go to home page",
            "refresh": "refresh page",
            
            # Window management
            "minimize": "minimize window",
            "maximize": "maximize window",
            "close window": "close current window",
            "switch window": "switch to next window",
            
            # Productivity shortcuts
            "focus mode": "start focus session",
            "break time": "take short break",
            "meeting time": "join next meeting",
            "check email": "open email client",
            
            # Agent shortcuts
            "clean up": "run janitor agent",
            "security check": "run security agent",
            "productivity tips": "run productivity agent"
        }
    
    async def start_voice_control(self):
        """Start the voice control system."""
        self.is_active = True
        logger.info("Enhanced voice control system started")
        
        # Initialize background tasks
        asyncio.create_task(self._wake_word_detection_loop())
        asyncio.create_task(self._proactive_suggestions_loop())
        asyncio.create_task(self._conversation_cleanup_loop())
    
    async def stop_voice_control(self):
        """Stop the voice control system."""
        self.is_active = False
        logger.info("Enhanced voice control system stopped")
    
    async def _wake_word_detection_loop(self):
        """Continuously listen for wake words."""
        while self.is_active:
            try:
                # This would integrate with actual speech recognition
                # For now, simulate wake word detection
                await asyncio.sleep(1)
                
                # In real implementation:
                # - Use continuous speech recognition
                # - Listen for wake words
                # - When detected, start full voice processing
                
            except Exception as e:
                logger.error(f"Wake word detection error: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def process_voice_input(
        self,
        audio_data: bytes,
        user_id: str = "default",
        context_id: Optional[str] = None
    ) -> VoiceResponse:
        """Process voice input and return response."""
        try:
            # Step 1: Convert audio to text (speech recognition)
            text = await self._speech_to_text(audio_data)
            
            if not text:
                return self._create_response("I didn't hear anything. Could you try again?")
            
            # Step 2: Parse intent from text
            intent = await self._parse_intent(text, user_id, context_id)
            
            # Step 3: Get or create conversation context
            if not context_id:
                context_id = str(uuid.uuid4())
            
            context = await self._get_or_create_context(context_id, user_id)
            context.intent_history.append(intent)
            context.last_interaction = datetime.now()
            
            # Step 4: Process intent based on conversation state
            if context.conversation_state == ConversationState.WAITING_CONFIRMATION:
                response = await self._handle_confirmation(intent, context)
            elif intent.context_dependent and context.conversation_state != ConversationState.MULTI_TURN:
                response = await self._handle_context_dependent_intent(intent, context)
            else:
                response = await self._execute_voice_command(intent, context)
            
            # Step 5: Update conversation state
            await self._update_conversation_state(context, intent, response)
            
            # Step 6: Store conversation in memory
            await self._store_conversation_turn(context, intent, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return self._create_response("I'm having trouble processing that. Please try again.")
    
    async def _speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech audio to text."""
        try:
            # This would integrate with speech recognition service
            # (Google Speech API, Azure Speech, etc.)
            # For now, simulate speech recognition
            
            # In real implementation:
            # - Use Google Speech-to-Text API
            # - Support multiple languages
            # - Handle noise cancellation
            # - Return confidence scores
            
            return "simulated speech recognition result"
            
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            return ""
    
    async def _parse_intent(self, text: str, user_id: str, context_id: Optional[str]) -> VoiceIntent:
        """Parse intent from recognized text."""
        text_lower = text.lower().strip()
        
        # Check for voice shortcuts first
        if text_lower in self.voice_shortcuts:
            text = self.voice_shortcuts[text_lower]
            text_lower = text.lower()
        
        # Parse entities and intent
        entities = {}
        confidence = 0.5
        intent_type = VoiceIntentType.COMMAND
        
        # Match against patterns
        for intent_name, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    entities.update(match.groupdict())
                    confidence = 0.9
                    break
            if confidence > 0.8:
                break
        
        # Determine intent type based on text structure
        if any(word in text_lower for word in ["what", "how", "when", "where", "why"]):
            intent_type = VoiceIntentType.QUESTION
        elif any(word in text_lower for word in ["yes", "no", "okay", "sure", "cancel"]):
            intent_type = VoiceIntentType.CONFIRMATION
        elif any(word in text_lower for word in ["clarify", "explain", "what do you mean"]):
            intent_type = VoiceIntentType.CLARIFICATION
        
        # Check if this requires confirmation (potentially dangerous actions)
        requires_confirmation = any(keyword in text_lower for keyword in [
            "delete", "remove", "uninstall", "format", "reset", "shutdown", "restart"
        ])
        
        # Detect emotional tone
        emotional_tone = self._detect_emotional_tone(text)
        
        # Detect language (simplified)
        language = "en"  # Default to English
        
        return VoiceIntent(
            intent_id=str(uuid.uuid4()),
            intent_type=intent_type,
            command=text,
            entities=entities,
            confidence=confidence,
            requires_confirmation=requires_confirmation,
            context_dependent=confidence < 0.7,
            original_text=text,
            language=language,
            emotional_tone=emotional_tone
        )
    
    def _detect_emotional_tone(self, text: str) -> str:
        """Detect emotional tone from text."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["please", "thank you", "thanks"]):
            return "polite"
        elif any(word in text_lower for word in ["urgent", "quickly", "asap", "now"]):
            return "urgent"
        elif any(word in text_lower for word in ["!", "damn", "frustrated"]):
            return "frustrated"
        elif any(word in text_lower for word in ["help", "confused", "lost"]):
            return "confused"
        else:
            return "neutral"
    
    async def _get_or_create_context(self, context_id: str, user_id: str) -> ConversationContext:
        """Get existing conversation context or create new one."""
        if context_id not in self.conversation_contexts:
            self.conversation_contexts[context_id] = ConversationContext(
                context_id=context_id,
                user_id=user_id,
                started_at=datetime.now(),
                last_interaction=datetime.now(),
                conversation_state=ConversationState.LISTENING,
                intent_history=[],
                entities_memory={},
                pending_actions=[],
                user_preferences=self.user_preferences.get(user_id, {})
            )
            self.active_context_id = context_id
        
        return self.conversation_contexts[context_id]
    
    async def _execute_voice_command(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Execute a voice command and return response."""
        command = intent.command.lower()
        
        # Handle different types of commands
        if intent.requires_confirmation and not context.conversation_state == ConversationState.WAITING_CONFIRMATION:
            # Store action for confirmation
            context.pending_actions.append({
                "intent": asdict(intent),
                "timestamp": datetime.now().isoformat()
            })
            context.conversation_state = ConversationState.WAITING_CONFIRMATION
            
            return self._create_response(
                self.response_templates["confirm_action"].format(action=intent.command),
                requires_user_response=True,
                suggested_responses=["Yes", "No", "Cancel"]
            )
        
        # Execute the command based on intent type
        try:
            if any(keyword in command for keyword in ["open", "launch", "start"]):
                return await self._handle_open_application(intent, context)
            elif any(keyword in command for keyword in ["close", "quit", "exit"]):
                return await self._handle_close_application(intent, context)
            elif any(keyword in command for keyword in ["click", "press", "tap"]):
                return await self._handle_click_element(intent, context)
            elif any(keyword in command for keyword in ["type", "write", "enter"]):
                return await self._handle_type_text(intent, context)
            elif any(keyword in command for keyword in ["agent", "run", "stop"]):
                return await self._handle_agent_command(intent, context)
            elif any(keyword in command for keyword in ["security", "scan"]):
                return await self._handle_security_command(intent, context)
            elif any(keyword in command for keyword in ["task", "remind", "meeting"]):
                return await self._handle_productivity_command(intent, context)
            else:
                return await self._handle_general_query(intent, context)
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return self._create_response(
                self.response_templates["action_failed"].format(
                    action=intent.command,
                    reason="An error occurred"
                )
            )
    
    async def _handle_confirmation(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle confirmation responses."""
        response_text = intent.command.lower()
        
        if any(word in response_text for word in ["yes", "okay", "sure", "proceed", "do it"]):
            # Execute pending action
            if context.pending_actions:
                pending_action = context.pending_actions.pop(0)
                pending_intent = VoiceIntent(**pending_action["intent"])
                
                # Execute the confirmed action
                context.conversation_state = ConversationState.PROCESSING
                result = await self._execute_voice_command(pending_intent, context)
                
                return self._create_response(
                    f"Executing {pending_intent.command}... {result.text}"
                )
            else:
                return self._create_response("There's nothing to confirm right now.")
        
        elif any(word in response_text for word in ["no", "cancel", "nevermind", "stop"]):
            # Cancel pending action
            context.pending_actions.clear()
            context.conversation_state = ConversationState.LISTENING
            
            return self._create_response("Okay, I've cancelled that action.")
        
        else:
            return self._create_response(
                "I need a yes or no answer. Should I proceed with the action?",
                requires_user_response=True,
                suggested_responses=["Yes", "No", "Cancel"]
            )
    
    async def _handle_context_dependent_intent(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle intents that require conversation context."""
        # Look at recent conversation history for context
        if context.intent_history:
            previous_intent = context.intent_history[-2] if len(context.intent_history) > 1 else None
            
            if previous_intent:
                # Try to resolve pronouns and references
                resolved_command = self._resolve_references(intent.command, previous_intent, context)
                intent.command = resolved_command
                intent.confidence = 0.8
                
                return await self._execute_voice_command(intent, context)
        
        # Need more context
        return self._create_response(
            self.response_templates["need_clarification"].format(
                question="What would you like me to do?"
            ),
            requires_user_response=True
        )
    
    def _resolve_references(self, current_command: str, previous_intent: VoiceIntent, context: ConversationContext) -> str:
        """Resolve pronouns and references in current command."""
        resolved = current_command
        
        # Simple pronoun resolution
        pronoun_replacements = {
            "it": previous_intent.entities.get("app_name", ""),
            "that": previous_intent.entities.get("target", ""),
            "there": previous_intent.entities.get("location", ""),
        }
        
        for pronoun, replacement in pronoun_replacements.items():
            if pronoun in resolved.lower() and replacement:
                resolved = resolved.replace(pronoun, replacement)
        
        return resolved
    
    async def _update_conversation_state(self, context: ConversationContext, intent: VoiceIntent, response: VoiceResponse):
        """Update conversation state based on intent and response."""
        if response.requires_user_response:
            if intent.requires_confirmation:
                context.conversation_state = ConversationState.WAITING_CONFIRMATION
            else:
                context.conversation_state = ConversationState.MULTI_TURN
        else:
            context.conversation_state = ConversationState.LISTENING
        
        # Update entities memory
        context.entities_memory.update(intent.entities)
        
        # Set session topic if this is the start of a focused conversation
        if len(context.intent_history) == 1:
            context.session_topic = intent.command.split()[0] if intent.command else None
    
    async def _store_conversation_turn(self, context: ConversationContext, intent: VoiceIntent, response: VoiceResponse):
        """Store conversation turn in memory."""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "context_id": context.context_id,
            "user_input": intent.original_text,
            "intent": asdict(intent),
            "response": asdict(response),
            "conversation_state": context.conversation_state.value
        }
        
        self.conversation_memory.append(turn)
        
        # Keep only recent conversation history (last 100 turns)
        if len(self.conversation_memory) > 100:
            self.conversation_memory = self.conversation_memory[-100:]
    
    # ===== Command Handler Methods =====
    
    async def _handle_open_application(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle application opening commands."""
        app_name = intent.entities.get("app_name", "").strip()
        
        if not app_name:
            return self._create_response(
                "Which application would you like me to open?",
                requires_user_response=True
            )
        
        # This would integrate with the actual automation system
        # For now, simulate application opening
        
        return self._create_response(
            self.response_templates["action_complete"].format(action=f"opened {app_name}")
        )
    
    async def _handle_close_application(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle application closing commands."""
        app_name = intent.entities.get("app_name", "").strip()
        
        if not app_name:
            return self._create_response(
                "Which application would you like me to close?",
                requires_user_response=True
            )
        
        return self._create_response(
            self.response_templates["action_complete"].format(action=f"closed {app_name}")
        )
    
    async def _handle_click_element(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle click element commands."""
        target = intent.entities.get("target", "").strip()
        
        if not target:
            return self._create_response(
                "What would you like me to click?",
                requires_user_response=True
            )
        
        return self._create_response(
            self.response_templates["action_complete"].format(action=f"clicked {target}")
        )
    
    async def _handle_type_text(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle text typing commands."""
        text = intent.entities.get("text", "").strip()
        
        if not text:
            return self._create_response(
                "What would you like me to type?",
                requires_user_response=True
            )
        
        return self._create_response(
            self.response_templates["action_complete"].format(action=f"typed '{text}'")
        )
    
    async def _handle_agent_command(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle agent-related commands."""
        agent_name = intent.entities.get("agent_name", "").strip()
        command = intent.command.lower()
        
        if "run" in command or "start" in command:
            if agent_name:
                return self._create_response(
                    self.response_templates["action_complete"].format(action=f"started {agent_name} agent")
                )
            else:
                return self._create_response(
                    "Which agent would you like me to run?",
                    requires_user_response=True,
                    suggested_responses=["Janitor Agent", "Security Agent", "Productivity Agent"]
                )
        
        elif "stop" in command:
            if agent_name:
                return self._create_response(
                    self.response_templates["action_complete"].format(action=f"stopped {agent_name} agent")
                )
            else:
                return self._create_response(
                    "Which agent would you like me to stop?",
                    requires_user_response=True
                )
        
        else:
            return self._create_response(
                "Here's the status of your agents: All agents are running normally.",
                requires_user_response=False
            )
    
    async def _handle_security_command(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle security-related commands."""
        return self._create_response(
            "Starting security scan... I'll notify you when it's complete.",
            requires_user_response=False
        )
    
    async def _handle_productivity_command(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle productivity-related commands."""
        command = intent.command.lower()
        
        if "task" in command:
            task_description = intent.entities.get("task_description", "")
            if task_description:
                return self._create_response(
                    self.response_templates["action_complete"].format(action=f"created task: {task_description}")
                )
        
        elif "meeting" in command:
            meeting_details = intent.entities.get("meeting_details", "")
            if meeting_details:
                return self._create_response(
                    self.response_templates["action_complete"].format(action=f"scheduled meeting: {meeting_details}")
                )
        
        elif "break" in command:
            break_type = intent.entities.get("break_type", "short")
            return self._create_response(
                self.response_templates["action_complete"].format(action=f"started {break_type} break timer")
            )
        
        return self._create_response(
            "I can help you create tasks, schedule meetings, or take breaks. What would you like to do?",
            requires_user_response=True
        )
    
    async def _handle_general_query(self, intent: VoiceIntent, context: ConversationContext) -> VoiceResponse:
        """Handle general queries and questions."""
        command = intent.command.lower()
        
        if "time" in command:
            current_time = datetime.now().strftime("%I:%M %p")
            return self._create_response(f"It's currently {current_time}.")
        
        elif "weather" in command:
            return self._create_response("I don't have access to weather data right now, but I can help you open a weather app.")
        
        elif "status" in command or "how are" in command:
            return self._create_response("All systems are running normally. Is there anything specific you'd like me to check?")
        
        else:
            return self._create_response(
                "I'm not sure how to help with that. Could you try rephrasing your request?",
                requires_user_response=True
            )
    
    # ===== Proactive Features =====
    
    async def _proactive_suggestions_loop(self):
        """Provide proactive suggestions based on user behavior."""
        while self.is_active:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                suggestion = await self._generate_proactive_suggestion()
                if suggestion:
                    # Send suggestion through notification system
                    from app.notifications.notification_manager import notify, NotificationPriority
                    await notify(
                        title="Voice Assistant Suggestion",
                        message=suggestion,
                        priority=NotificationPriority.LOW,
                        agent_name="VOICE_CONTROL"
                    )
                    
            except Exception as e:
                logger.error(f"Proactive suggestions error: {e}")
                await asyncio.sleep(60)
    
    async def _generate_proactive_suggestion(self) -> Optional[str]:
        """Generate proactive suggestions based on patterns."""
        current_time = datetime.now()
        
        # Check if it's been a while since last break
        if hasattr(self, 'last_break_time'):
            if (current_time - self.last_break_time).total_seconds() > 3600:  # 1 hour
                return self.response_templates["productivity_suggestion"]
        
        # Check if security scan is due
        if hasattr(self, 'last_security_scan'):
            if (current_time - self.last_security_scan).total_seconds() > 86400:  # 1 day
                return self.response_templates["security_reminder"]
        
        # Check if file cleanup is needed
        if hasattr(self, 'last_cleanup'):
            if (current_time - self.last_cleanup).total_seconds() > 604800:  # 1 week
                return self.response_templates["maintenance_suggestion"]
        
        return None
    
    async def _conversation_cleanup_loop(self):
        """Clean up old conversation contexts."""
        while self.is_active:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                expired_contexts = []
                
                for context_id, context in self.conversation_contexts.items():
                    # Remove contexts older than 24 hours
                    if (current_time - context.last_interaction).total_seconds() > 86400:
                        expired_contexts.append(context_id)
                
                for context_id in expired_contexts:
                    del self.conversation_contexts[context_id]
                    logger.info(f"Cleaned up expired conversation context: {context_id}")
                    
            except Exception as e:
                logger.error(f"Conversation cleanup error: {e}")
    
    # ===== Utility Methods =====
    
    def _create_response(
        self,
        text: str,
        requires_user_response: bool = False,
        suggested_responses: Optional[List[str]] = None,
        emotional_tone: str = "neutral"
    ) -> VoiceResponse:
        """Create a voice response."""
        return VoiceResponse(
            response_id=str(uuid.uuid4()),
            text=text,
            voice_settings={"speed": 1.0, "pitch": 1.0, "volume": 0.8},
            requires_user_response=requires_user_response,
            suggested_responses=suggested_responses or [],
            emotional_tone=emotional_tone
        )
    
    def add_custom_command(self, command_phrase: str, handler_function: callable):
        """Add a custom voice command."""
        self.custom_commands[command_phrase.lower()] = handler_function
        logger.info(f"Added custom voice command: {command_phrase}")
    
    def add_voice_shortcut(self, shortcut_phrase: str, expanded_command: str):
        """Add a voice shortcut."""
        self.voice_shortcuts[shortcut_phrase.lower()] = expanded_command
        logger.info(f"Added voice shortcut: {shortcut_phrase} -> {expanded_command}")
    
    def get_conversation_history(self, context_id: Optional[str] = None) -> List[Dict]:
        """Get conversation history."""
        if context_id:
            return [turn for turn in self.conversation_memory if turn["context_id"] == context_id]
        return self.conversation_memory
    
    def get_active_contexts(self) -> List[ConversationContext]:
        """Get all active conversation contexts."""
        return list(self.conversation_contexts.values())


# Global voice control instance
_voice_control = None


def get_voice_control() -> EnhancedVoiceControl:
    """Get the global voice control instance."""
    global _voice_control
    if _voice_control is None:
        _voice_control = EnhancedVoiceControl()
    return _voice_control