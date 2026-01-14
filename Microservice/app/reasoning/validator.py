"""
Gemini Reasoning Layer - Plan Validator

Validates Gemini output to ensure safety and correctness.
Rejects hallucinated skills, over-complex plans, and low-confidence responses.
"""

from typing import Dict, Any, List, Tuple, Optional
from .skills import REGISTERED_SKILLS, is_valid_skill


class PlanValidator:
    """
    Validates Gemini output against strict rules.
    
    Rules:
    - All skills must be registered
    - Max 5 steps for planning, 3 for recovery
    - Minimum confidence threshold
    - Valid JSON structure
    """
    
    def __init__(
        self,
        max_plan_steps: int = 5,
        max_recovery_steps: int = 3,
        min_confidence: float = 0.6
    ):
        self.max_plan_steps = max_plan_steps
        self.max_recovery_steps = max_recovery_steps
        self.min_confidence = min_confidence
    
    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a planning response from Gemini.
        
        Returns:
            (is_valid, error_message)
        """
        if not plan:
            return False, "Plan is empty or None"
        
        # Check required fields
        if "plan" not in plan:
            return False, "Missing 'plan' field"
        
        if "confidence" not in plan:
            return False, "Missing 'confidence' field"
        
        # Check confidence threshold
        confidence = plan.get("confidence", 0)
        if not isinstance(confidence, (int, float)):
            return False, "Confidence must be a number"
        
        if confidence < self.min_confidence:
            return False, f"Confidence {confidence} below threshold {self.min_confidence}"
        
        # Check step count
        steps = plan.get("plan", [])
        if not isinstance(steps, list):
            return False, "Plan must be a list"
        
        if len(steps) > self.max_plan_steps:
            return False, f"Plan has {len(steps)} steps, max is {self.max_plan_steps}"
        
        if len(steps) == 0:
            return False, "Plan has no steps"
        
        # Validate each step
        for i, step in enumerate(steps):
            valid, error = self._validate_step(step, i + 1)
            if not valid:
                return False, error
        
        return True, None
    
    def validate_recovery(self, recovery: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a recovery response from Gemini.
        
        Returns:
            (is_valid, error_message)
        """
        if not recovery:
            return False, "Recovery is empty or None"
        
        # Check for abort flag
        if recovery.get("should_abort", False):
            return True, None  # Valid abort response
        
        # Check required fields
        if "recovery_plan" not in recovery:
            return False, "Missing 'recovery_plan' field"
        
        # Check step count (stricter for recovery)
        steps = recovery.get("recovery_plan", [])
        if not isinstance(steps, list):
            return False, "Recovery plan must be a list"
        
        if len(steps) > self.max_recovery_steps:
            return False, f"Recovery has {len(steps)} steps, max is {self.max_recovery_steps}"
        
        # Validate each step
        for i, step in enumerate(steps):
            valid, error = self._validate_step(step, i + 1)
            if not valid:
                return False, error
        
        return True, None
    
    def _validate_step(self, step: Dict[str, Any], step_num: int) -> Tuple[bool, Optional[str]]:
        """Validate a single step."""
        if not isinstance(step, dict):
            return False, f"Step {step_num} is not a dictionary"
        
        # Check skill exists
        skill_name = step.get("skill", "")
        if not skill_name:
            return False, f"Step {step_num} missing 'skill' field"
        
        if not is_valid_skill(skill_name):
            return False, f"Step {step_num} has unknown skill: '{skill_name}'"
        
        # Check params is a dict (if present)
        params = step.get("params", {})
        if not isinstance(params, dict):
            return False, f"Step {step_num} params must be a dictionary"
        
        return True, None
    
    def sanitize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a plan by removing any extra fields.
        Only keeps known safe fields.
        """
        if not plan:
            return None
        
        sanitized = {
            "intent_summary": plan.get("intent_summary", ""),
            "confidence": float(plan.get("confidence", 0)),
            "fallback_available": bool(plan.get("fallback_available", True)),
            "plan": []
        }
        
        for step in plan.get("plan", []):
            clean_step = {
                "step": step.get("step", 0),
                "skill": step.get("skill", ""),
                "params": step.get("params", {}),
                "rationale": step.get("rationale", "")
            }
            sanitized["plan"].append(clean_step)
        
        return sanitized
