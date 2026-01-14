"""
Gemini Reasoning Layer - Main Integration

🧠 Philosophy: "Gemini thinks. Python decides. C# executes."

This layer:
✅ Interprets natural user intent
✅ Produces structured action plans
✅ Enables failure recovery
❌ NEVER executes commands
❌ NEVER communicates with C# directly
"""

import json
import os
from typing import Dict, Any, Optional, List
from google import genai

from .skills import REGISTERED_SKILLS, get_skill_action
from .prompts import build_planning_prompt, build_recovery_prompt
from .validator import PlanValidator


class GeminiReasoningLayer:
    """
    Gemini-powered reasoning layer for desktop automation.
    
    This layer converts natural language commands into validated
    action plans that can be executed by the command builder.
    
    Gemini ONLY outputs plans - execution is handled by Python + C#.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        model_id: str = "gemini-2.5-flash",
        max_plan_steps: int = 5,
        max_recovery_steps: int = 3,
        min_confidence: float = 0.6,
        timeout_seconds: int = 10
    ):
        self.enabled = enabled
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        
        # Initialize Gemini client
        self.client = None
        if enabled:
            try:
                self.client = genai.Client()
            except Exception as e:
                print(f"[GEMINI] Failed to initialize client: {e}")
                self.enabled = False
        
        # Initialize validator
        self.validator = PlanValidator(
            max_plan_steps=max_plan_steps,
            max_recovery_steps=max_recovery_steps,
            min_confidence=min_confidence
        )
    
    async def plan(
        self,
        user_command: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Convert user intent to validated action plan.
        
        Args:
            user_command: Natural language command from user
            context: Optional context (active window, recent actions, etc.)
        
        Returns:
            Validated plan dict, or None if planning fails
            (falls back to deterministic logic when None)
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Build prompts
            context = context or {}
            system_prompt, user_prompt = build_planning_prompt(
                user_command=user_command,
                active_window=context.get("active_window", "Unknown"),
                recent_actions=context.get("recent_actions", "None"),
                failures=context.get("failures", "None")
            )
            
            # Call Gemini
            response = await self._call_gemini(system_prompt, user_prompt)
            
            if not response:
                return None
            
            # Parse JSON response
            plan = self._parse_json_response(response)
            
            if not plan:
                return None
            
            # Validate plan
            is_valid, error = self.validator.validate_plan(plan)
            
            if not is_valid:
                print(f"[GEMINI] Plan validation failed: {error}")
                return None
            
            # Sanitize and return
            return self.validator.sanitize_plan(plan)
            
        except Exception as e:
            print(f"[GEMINI] Planning error: {e}")
            return None
    
    async def recover(
        self,
        original_plan: Dict[str, Any],
        failed_step: Dict[str, Any],
        failure_reason: str,
        attempt: int = 1,
        max_attempts: int = 2,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Propose recovery plan after execution failure.
        
        Args:
            original_plan: The plan that failed
            failed_step: The step that failed
            failure_reason: Why it failed
            attempt: Current recovery attempt number
            max_attempts: Maximum recovery attempts
            context: Additional context
        
        Returns:
            Recovery plan dict, or None if recovery is not possible
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Build recovery prompts
            system_prompt, user_prompt = build_recovery_prompt(
                original_plan=original_plan,
                failed_step=failed_step,
                failure_reason=failure_reason,
                attempt=attempt,
                max_attempts=max_attempts
            )
            
            # Call Gemini
            response = await self._call_gemini(system_prompt, user_prompt)
            
            if not response:
                return None
            
            # Parse JSON response
            recovery = self._parse_json_response(response)
            
            if not recovery:
                return None
            
            # Check if Gemini suggests abort
            if recovery.get("should_abort", False):
                print(f"[GEMINI] Recovery aborted: {recovery.get('failure_analysis', 'Unknown reason')}")
                return None
            
            # Validate recovery plan
            is_valid, error = self.validator.validate_recovery(recovery)
            
            if not is_valid:
                print(f"[GEMINI] Recovery validation failed: {error}")
                return None
            
            return recovery
            
        except Exception as e:
            print(f"[GEMINI] Recovery error: {e}")
            return None
    
    def convert_plan_to_actions(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert validated Gemini plan to action steps.
        
        This bridges Gemini's skill-based plan to the existing
        action format expected by the command builder.
        """
        actions = []
        
        for step in plan.get("plan", []):
            skill_name = step.get("skill", "")
            params = step.get("params", {})
            
            # Get action type from skill registry
            action_type = get_skill_action(skill_name)
            
            if not action_type:
                continue
            
            # Build action dict
            action = {"action": action_type}
            
            # Map params based on skill
            if "target" in params:
                action["target"] = params["target"]
            if "text" in params:
                action["content"] = params["text"]
            if "url" in params:
                action["url"] = params["url"]
            if "query" in params:
                action["query"] = params["query"]
            if "amount" in params:
                action["amount"] = params["amount"]
            if "direction" in params:
                action["direction"] = params["direction"]
            if "seconds" in params:
                action["seconds"] = params["seconds"]
            if "key" in params:
                action["key"] = params["key"]
            
            actions.append(action)
        
        return actions
    
    async def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Optional[str]:
        """Call Gemini API with prompts."""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
                ],
                config={
                    "temperature": 0.1,  # Very low for deterministic output
                    "max_output_tokens": 1024,
                }
            )
            
            if response and response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            print(f"[GEMINI] API call failed: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Gemini response, handling markdown code blocks."""
        if not response:
            return None
        
        text = response.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[GEMINI] JSON parse error: {e}")
            print(f"[GEMINI] Raw response: {text[:200]}...")
            return None
