"""
Recovery Planner - Orchestrates vision-based failure recovery.

Flow:
1. Action fails -> Capture screenshot
2. Pass ExecutionContext to Vision
3. Vision analyzes with full context
4. Get recovery action
5. Execute recovery
6. Feed result back to context
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from .screen_capture import capture_screen_base64
from .vision_analyzer import get_vision_analyzer

logger = logging.getLogger(__name__)

# Maximum recovery attempts to prevent infinite loops
MAX_RECOVERY_ATTEMPTS = 3

# Minimum confidence to attempt recovery
MIN_CONFIDENCE = 0.5


@dataclass
class ExecutionContext:
    """
    Shared context between Vision and LLM.
    Tracks desktop state for intelligent decision-making.
    """
    original_goal: str = ""
    current_step: int = 0
    total_steps: int = 0
    focused_window: str = ""
    focused_process: str = ""
    opened_apps: List[str] = field(default_factory=list)
    last_action: str = ""
    last_result: bool = True
    last_error: str = ""
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    vision_observations: List[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Convert to text for vision prompt."""
        ctx = f"""EXECUTION CONTEXT:
- Goal: {self.original_goal}
- Step: {self.current_step}/{self.total_steps}
- Focused Window: {self.focused_window or 'unknown'}
- Process: {self.focused_process or 'unknown'}
- Recently Opened: {', '.join(self.opened_apps[-3:]) if self.opened_apps else 'none'}
- Last Action: {self.last_action}
- Last Result: {'SUCCESS' if self.last_result else 'FAILED - ' + self.last_error}

RECENT OBSERVATIONS:
{chr(10).join('- ' + o for o in self.vision_observations[-3:]) if self.vision_observations else '- No prior observations'}
"""
        return ctx
    
    def add_observation(self, observation: str):
        """Add a vision observation."""
        self.vision_observations.append(observation)
        # Keep last 10
        if len(self.vision_observations) > 10:
            self.vision_observations = self.vision_observations[-10:]
    
    def record_action(self, action: str, target: str, result: bool, error: str = ""):
        """Record an action result."""
        self.action_history.append({
            "action": action,
            "target": target,
            "result": result,
            "error": error
        })
        self.last_action = f"{action}({target})" if target else action
        self.last_result = result
        self.last_error = error


# Global context (singleton)
_execution_context: Optional[ExecutionContext] = None


def get_execution_context() -> ExecutionContext:
    """Get singleton ExecutionContext."""
    global _execution_context
    if _execution_context is None:
        _execution_context = ExecutionContext()
    return _execution_context


def reset_execution_context():
    """Reset context for new goal."""
    global _execution_context
    _execution_context = ExecutionContext()


class RecoveryPlanner:
    """
    Orchestrates the recovery loop when actions fail.
    
    perception → reasoning → action → verification
    """
    
    def __init__(self):
        self.vision = get_vision_analyzer()
        self.recovery_history: List[Dict[str, Any]] = []
    
    def attempt_recovery(
        self,
        original_goal: str,
        failed_action: str,
        error_reason: str
    ) -> Dict[str, Any]:
        """
        Attempt to recover from a failed action.
        
        Args:
            original_goal: What the user wanted to do
            failed_action: The action that failed
            error_reason: Why it failed
        
        Returns:
            Recovery result with suggested action or failure
        """
        logger.info(f"[RECOVERY] Starting recovery for failed action: {failed_action}")
        logger.info(f"[RECOVERY] Original goal: {original_goal}")
        logger.info(f"[RECOVERY] Error: {error_reason}")
        
        # Check if we've exceeded max attempts
        recent_failures = [
            h for h in self.recovery_history[-5:]
            if h.get("goal") == original_goal
        ]
        
        if len(recent_failures) >= MAX_RECOVERY_ATTEMPTS:
            logger.warning("[RECOVERY] Max attempts exceeded, giving up")
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "max_attempts_exceeded",
                "message": "Too many recovery attempts. Manual intervention needed."
            }
        
        # Step 1: Capture screen
        logger.info("[RECOVERY] Capturing screen...")
        screenshot = capture_screen_base64()
        
        if not screenshot:
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "screenshot_failed",
                "message": "Could not capture screen"
            }
        
        # Step 2: Analyze with vision
        logger.info("[RECOVERY] Analyzing screen with Gemini Vision...")
        analysis = self.vision.analyze_screen(
            screenshot_base64=screenshot,
            original_goal=original_goal,
            failed_action=failed_action,
            context_text=get_execution_context().to_prompt_context()
        )
        
        if not analysis.get("success"):
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "vision_failed",
                "message": analysis.get("error", "Vision analysis failed")
            }
        
        # Step 3: Check if goal is already achieved
        if analysis.get("goal_achieved") is True:
            logger.info("[RECOVERY] Vision indicates goal already achieved")
            return {
                "success": True,
                "recovery_possible": True,
                "analysis": analysis,
                "recovery_action": {"action": "none", "reasoning": "Goal already achieved"},
                "confidence": analysis.get("confidence", 0),
                "blocker": analysis.get("blocker"),
                "current_state": analysis.get("current_state"),
            }

        # Step 4: Check confidence
        confidence = analysis.get("confidence", 0)
        if confidence < MIN_CONFIDENCE:
            logger.warning(f"[RECOVERY] Low confidence ({confidence}), asking user")
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "low_confidence",
                "confidence": confidence,
                "analysis": analysis,
                "message": "Unsure how to proceed. Please help."
            }
        
        # Step 5: Get recovery action
        recovery_action = self.vision.get_recovery_action(analysis, original_goal)
        
        if not recovery_action:
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "no_recovery_action",
                "analysis": analysis,
                "message": "Could not determine recovery action"
            }
        
        # Record attempt
        self.recovery_history.append({
            "goal": original_goal,
            "failed_action": failed_action,
            "analysis": analysis,
            "recovery_action": recovery_action
        })
        
        logger.info(f"[RECOVERY] Suggested action: {recovery_action.get('action')}")
        logger.info(f"[RECOVERY] Reasoning: {recovery_action.get('reasoning')}")
        
        return {
            "success": True,
            "recovery_possible": True,
            "analysis": analysis,
            "recovery_action": recovery_action,
            "confidence": confidence,
            "blocker": analysis.get("blocker"),
            "current_state": analysis.get("current_state")
        }
    
    def clear_history(self):
        """Clear recovery history (call after successful goal completion)."""
        self.recovery_history.clear()


# Singleton instance
_recovery_planner: Optional[RecoveryPlanner] = None


def get_recovery_planner() -> RecoveryPlanner:
    """Get singleton RecoveryPlanner instance."""
    global _recovery_planner
    if _recovery_planner is None:
        _recovery_planner = RecoveryPlanner()
    return _recovery_planner


def attempt_recovery(
    original_goal: str,
    failed_action: str,
    error_reason: str = "unknown"
) -> Dict[str, Any]:
    """
    Convenience function to attempt recovery.
    
    Args:
        original_goal: What user wanted
        failed_action: What failed
        error_reason: Why it failed
    
    Returns:
        Recovery result with suggested action
    """
    planner = get_recovery_planner()
    return planner.attempt_recovery(original_goal, failed_action, error_reason)
