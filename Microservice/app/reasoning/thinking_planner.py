"""
Advanced planner using Gemini 2.0 Flash Thinking for complex multi-step workflows.
Leverages extended reasoning mode for better planning quality.
"""
import json
import logging
from typing import Optional, Dict, Any, List
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThinkingPlanner:
    """
    Uses Gemini 2.0 Flash Thinking to create detailed execution plans
    for complex multi-step automation workflows.
    
    Thinking mode provides:
    - Extended reasoning for complex tasks
    - Better contingency planning
    - More accurate verification steps
    - Higher quality multi-step sequences
    """
    
    def __init__(self):
        """Initialize thinking planner with Gemini client."""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "gemini-2.0-flash-thinking-exp-01-21"
        logger.info(f"[THINKING_PLANNER] Initialized with model: {self.model_id}")
    
    async def plan_complex_workflow(
        self, 
        intent: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a detailed execution plan for a complex workflow.
        
        Args:
            intent: User's goal in natural language
            context: Current system context (active window, open apps, etc.)
            
        Returns:
            Dict with execution plan including main steps, verification, fallbacks
        """
        context = context or {}
        
        prompt = self._build_thinking_prompt(intent, context)
        
        try:
            logger.info(f"[THINKING_PLANNER] Planning workflow for: {intent}")
            
            # Use thinking mode with structured output
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "temperature": 0.3,  # Higher for creative problem-solving
                    "max_output_tokens": 2048,  # More space for detailed reasoning
                    "response_mime_type": "application/json",
                    "response_schema": self._get_workflow_schema()
                }
            )
            
            if response and response.text:
                plan = json.loads(response.text)
                logger.info(f"[THINKING_PLANNER] Generated plan with {len(plan.get('steps', []))} steps")
                return plan
            
            return None
            
        except Exception as e:
            logger.error(f"[THINKING_PLANNER] Error: {e}")
            return None
    
    def _build_thinking_prompt(self, intent: str, context: Dict[str, Any]) -> str:
        """Build prompt for thinking mode."""
        return f"""
You are an expert desktop automation planner using extended reasoning to create robust execution plans.

USER GOAL: {intent}

CURRENT CONTEXT:
- Active Window: {context.get('active_window', 'Unknown')}
- Open Applications: {', '.join(context.get('open_apps', [])) or 'None'}
- Recent Actions: {context.get('recent_actions', [])}
- Current Screen State: {context.get('screen_state', 'Unknown')}

THINK STEP-BY-STEP:

1. **Goal Analysis**: What is the user really trying to achieve? Break down the goal into sub-objectives.

2. **Resource Planning**: What applications need to be running? What state should they be in?

3. **Action Sequence**: What's the optimal order of operations? Consider:
   - Dependencies between steps
   - Timing requirements
   - Window focus management
   - Potential race conditions

4. **Error Scenarios**: What could go wrong at each step? Plan for:
   - Application not responding
   - UI elements not found
   - Unexpected dialogs
   - Network issues
   - File system errors

5. **Verification Strategy**: How will we know each step succeeded? Define:
   - Expected outcomes
   - Verification methods
   - Timeout thresholds
   - Success criteria

6. **Contingency Actions**: If a step fails, what are the fallback options?

OUTPUT FORMAT:
Provide a detailed execution plan as JSON with:
- reasoning: Your step-by-step thought process
- steps: Array of actions with verification
- estimated_time: Total execution time estimate
- risk_assessment: Potential failure points
- contingencies: Fallback actions for failures
- confidence: Overall confidence score (0.0-1.0)

Focus on creating a robust, production-ready plan that handles edge cases gracefully.
"""
    
    def _get_workflow_schema(self) -> dict:
        """Get JSON schema for workflow plan."""
        return {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Detailed reasoning process"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "target": {"type": "string"},
                            "content": {"type": "string"},
                            "expected_outcome": {
                                "type": "object",
                                "properties": {
                                    "window_title_contains": {"type": "string"},
                                    "element_present": {"type": "string"},
                                    "timeout_ms": {"type": "integer"}
                                }
                            },
                            "verification_method": {"type": "string"},
                            "timeout_ms": {"type": "integer"},
                            "priority": {"type": "string", "enum": ["critical", "important", "optional"]}
                        },
                        "required": ["action"]
                    }
                },
                "estimated_time": {
                    "type": "integer",
                    "description": "Estimated execution time in milliseconds"
                },
                "risk_assessment": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_index": {"type": "integer"},
                            "risk": {"type": "string"},
                            "probability": {"type": "string", "enum": ["low", "medium", "high"]},
                            "mitigation": {"type": "string"}
                        }
                    }
                },
                "contingencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trigger_condition": {"type": "string"},
                            "fallback_action": {"type": "string"}
                        }
                    }
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["steps", "confidence"]
        }
    
    def should_use_thinking_mode(self, intent: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if thinking mode should be used for this intent.
        
        Thinking mode is beneficial for:
        - Multi-app workflows (5+ steps)
        - Conditional logic
        - Error recovery
        - File operations with verification
        - Complex search/filter operations
        """
        context = context or {}
        intent_lower = intent.lower()
        
        # Complex indicators
        has_conditional = any(word in intent_lower for word in ["if", "when", "unless"])
        has_multiple_apps = sum(1 for app in ["chrome", "notepad", "excel", "slack"] if app in intent_lower) >= 2
        has_file_ops = any(op in intent_lower for op in ["save", "download", "export"])
        is_recovery = any(word in intent_lower for word in ["fix", "retry", "recover"])
        
        # Step count estimation
        step_words = ["and", "then", "after"]
        estimated_steps = sum(1 for word in step_words if word in intent_lower) + 1
        
        # Use thinking mode if:
        return (
            estimated_steps >= 5 or
            has_conditional or
            has_multiple_apps or
            (has_file_ops and estimated_steps >= 3) or
            is_recovery
        )


# Singleton instance
_thinking_planner_instance: Optional[ThinkingPlanner] = None


def get_thinking_planner() -> ThinkingPlanner:
    """Get singleton thinking planner instance."""
    global _thinking_planner_instance
    if _thinking_planner_instance is None:
        _thinking_planner_instance = ThinkingPlanner()
    return _thinking_planner_instance
