"""
Recovery Planner - Orchestrates vision-based failure recovery.

Flow:
1. Action fails -> Capture screenshot
2. Analyze with Gemini Vision
3. Get recovery action
4. Execute recovery
5. Verify success
"""

import logging
from typing import Dict, Any, Optional, List
from .screen_capture import capture_screen_base64
from .vision_analyzer import get_vision_analyzer

logger = logging.getLogger(__name__)

# Maximum recovery attempts to prevent infinite loops
MAX_RECOVERY_ATTEMPTS = 3

# Minimum confidence to attempt recovery
MIN_CONFIDENCE = 0.5


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
            failed_action=failed_action
        )
        
        if not analysis.get("success"):
            return {
                "success": False,
                "recovery_possible": False,
                "reason": "vision_failed",
                "message": analysis.get("error", "Vision analysis failed")
            }
        
        # Step 3: Check confidence
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
        
        # Step 4: Get recovery action
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
