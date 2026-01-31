"""
Intelligent model router for selecting appropriate Gemini model based on task.
Routes to Gemini 2.0 Flash Thinking for complex tasks, Gemini 2.0 Flash for standard tasks.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"          # Single action (open app, type text)
    MEDIUM = "medium"          # 2-4 steps, linear flow
    COMPLEX = "complex"        # 5+ steps, conditional logic
    VERY_COMPLEX = "very_complex"  # Multi-app workflows, error recovery


class TaskType(Enum):
    """Types of tasks."""
    VISION = "vision"          # Screenshot analysis
    PLANNING = "planning"      # Action sequence generation
    CHAT = "chat"             # Conversational response
    RECOVERY = "recovery"     # Error recovery suggestion


@dataclass
class ModelRoutingDecision:
    """Decision about which model to use."""
    model_id: str
    temperature: float
    max_tokens: int
    use_thinking: bool
    use_structured_output: bool
    reasoning: str


class ModelRouter:
    """
    Intelligently routes requests to appropriate Gemini model.
    
    Models:
    - gemini-2.0-flash-thinking-exp: Complex reasoning, multi-step planning
    - gemini-2.0-flash-exp: Fast standard tasks, vision
    - gemini-1.5-flash-002: Legacy fallback
    """
    
    # Model identifiers
    THINKING = "gemini-2.0-flash-thinking-exp-01-21"
    FLASH = "gemini-2.0-flash-exp"
    LEGACY = "gemini-1.5-flash-002"
    
    # Availability flags (can be toggled based on API availability)
    ENABLE_THINKING = True
    ENABLE_FLASH_2 = True
    
    def __init__(self):
        """Initialize model router."""
        self.models = {
            "thinking": self.THINKING,
            "fast": self.FLASH if self.ENABLE_FLASH_2 else self.LEGACY,
            "vision": self.FLASH if self.ENABLE_FLASH_2 else self.LEGACY,
            "legacy": self.LEGACY
        }
        logger.info(f"[MODEL_ROUTER] Initialized with models: {self.models}")
    
    def route(
        self, 
        task_type: TaskType,
        complexity: TaskComplexity,
        context: Optional[dict] = None
    ) -> ModelRoutingDecision:
        """
        Route to appropriate model based on task characteristics.
        
        Args:
            task_type: Type of task (vision, planning, chat, recovery)
            complexity: Task complexity level
            context: Optional context with user tier, preferences, etc.
            
        Returns:
            ModelRoutingDecision with model_id and parameters
        """
        context = context or {}
        
        # Vision tasks always use vision model
        if task_type == TaskType.VISION:
            decision = ModelRoutingDecision(
                model_id=self.models["vision"],
                temperature=0.2,
                max_tokens=1024,
                use_thinking=False,
                use_structured_output=True,
                reasoning="Vision analysis requires multimodal model"
            )
            self._record_decision(task_type, complexity, decision.model_id)
            return decision
        
        # Complex planning uses thinking mode (if enabled)
        if task_type == TaskType.PLANNING and complexity in [
            TaskComplexity.COMPLEX, 
            TaskComplexity.VERY_COMPLEX
        ] and self.ENABLE_THINKING:
            decision = ModelRoutingDecision(
                model_id=self.models["thinking"],
                temperature=0.3,
                max_tokens=2048,
                use_thinking=True,
                use_structured_output=True,
                reasoning=f"Complex {complexity.value} planning benefits from extended reasoning"
            )
            self._record_decision(task_type, complexity, decision.model_id)
            return decision
        
        # Recovery scenarios use thinking for problem-solving (if enabled)
        if task_type == TaskType.RECOVERY and self.ENABLE_THINKING:
            decision = ModelRoutingDecision(
                model_id=self.models["thinking"],
                temperature=0.4,
                max_tokens=1536,
                use_thinking=True,
                use_structured_output=True,
                reasoning="Error recovery requires creative problem-solving"
            )
            self._record_decision(task_type, complexity, decision.model_id)
            return decision
        
        # Chat uses moderate temperature for natural responses
        if task_type == TaskType.CHAT:
            decision = ModelRoutingDecision(
                model_id=self.models["fast"],
                temperature=0.7,
                max_tokens=600,
                use_thinking=False,
                use_structured_output=False,  # Chat doesn't need structured output
                reasoning="Conversational response with natural temperature"
            )
            self._record_decision(task_type, complexity, decision.model_id)
            return decision
        
        # Default: fast model for simple/medium tasks
        decision = ModelRoutingDecision(
            model_id=self.models["fast"],
            temperature=0.1,
            max_tokens=1024,
            use_thinking=False,
            use_structured_output=True,
            reasoning=f"Standard {complexity.value} planning with deterministic output"
        )
        self._record_decision(task_type, complexity, decision.model_id)
        return decision
    
    def estimate_complexity(self, intent: str, context: Optional[dict] = None) -> TaskComplexity:
        """
        Estimate task complexity from user intent and context.
        
        Args:
            intent: User's natural language command
            context: Optional context (open apps, recent actions, etc.)
            
        Returns:
            TaskComplexity enum value
        """
        context = context or {}
        intent_lower = intent.lower()
        
        # Multi-step indicators
        step_indicators = ["and", "then", "after", "next", "followed by"]
        num_steps = sum(1 for ind in step_indicators if ind in intent_lower)
        
        # Conditional logic indicators
        conditional_words = ["if", "when", "unless", "in case", "should", "check"]
        has_conditional = any(word in intent_lower for word in conditional_words)
        
        # App mentions (requires coordination between apps)
        app_keywords = [
            "chrome", "notepad", "excel", "word", "slack", "discord", 
            "outlook", "teams", "vscode", "spotify", "calculator"
        ]
        app_mentions = sum(1 for app in app_keywords if app in intent_lower)
        
        # Error recovery indicators
        recovery_words = ["fix", "undo", "recover", "retry", "try again", "didn't work"]
        is_recovery = any(word in intent_lower for word in recovery_words)
        
        # File operations (often complex)
        file_ops = ["save", "download", "upload", "export", "import", "move", "copy"]
        has_file_ops = any(op in intent_lower for op in file_ops)
        
        # Calculate complexity score
        score = 0
        score += num_steps * 1.5  # Each step adds complexity
        score += 3 if has_conditional else 0  # Conditional logic is complex
        score += app_mentions * 2  # Multiple apps need coordination
        score += 3 if is_recovery else 0  # Recovery requires reasoning
        score += 1 if has_file_ops else 0  # File ops add complexity
        
        # Check context for additional complexity
        if context:
            open_apps = context.get("open_apps", [])
            if len(open_apps) > 3:
                score += 1  # Many open apps increases complexity
        
        # Map score to complexity level
        if score >= 8:
            return TaskComplexity.VERY_COMPLEX
        elif score >= 5:
            return TaskComplexity.COMPLEX
        elif score >= 2:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def get_model_stats(self) -> dict:
        """Get model availability and configuration stats."""
        return {
            "thinking_enabled": self.ENABLE_THINKING,
            "flash_2_enabled": self.ENABLE_FLASH_2,
            "models": self.models,
            "available_models": {
                "thinking": self.THINKING if self.ENABLE_THINKING else None,
                "fast": self.models["fast"],
                "vision": self.models["vision"],
                "legacy": self.LEGACY
            }
        }
    
    def get_stats(self) -> dict:
        """Get routing statistics for monitoring."""
        if not hasattr(self, '_stats'):
            self._stats = {
                "total_decisions": 0,
                "decisions_by_type": {},
                "decisions_by_complexity": {},
                "models_used": {}
            }
        return self._stats.copy()
    
    def _record_decision(self, task_type: TaskType, complexity: TaskComplexity, model_id: str):
        """Record a routing decision for stats."""
        if not hasattr(self, '_stats'):
            self._stats = {
                "total_decisions": 0,
                "decisions_by_type": {},
                "decisions_by_complexity": {},
                "models_used": {}
            }
        
        self._stats["total_decisions"] += 1
        self._stats["decisions_by_type"][task_type.value] = \
            self._stats["decisions_by_type"].get(task_type.value, 0) + 1
        self._stats["decisions_by_complexity"][complexity.value] = \
            self._stats["decisions_by_complexity"].get(complexity.value, 0) + 1
        self._stats["models_used"][model_id] = \
            self._stats["models_used"].get(model_id, 0) + 1
    
    def _reset_stats(self):
        """Reset statistics (useful for testing)."""
        self._stats = {
            "total_decisions": 0,
            "decisions_by_type": {},
            "decisions_by_complexity": {},
            "models_used": {}
        }


# Singleton instance
_router_instance: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get singleton model router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance
