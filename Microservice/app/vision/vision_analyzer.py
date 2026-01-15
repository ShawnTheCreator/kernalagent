"""
Vision Analyzer - Gemma 3 Vision for UI Understanding

Analyzes screenshots to understand UI state and suggest recovery actions.
Uses task-aware prompting for accurate perception.
Uses Google's Gemma 3 27B vision model.
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Import Google Generative AI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("Google GenAI not available - vision analysis disabled")


class VisionAnalyzer:
    """
    Analyzes screenshots using Gemma 3 Vision to understand UI state
    and suggest recovery actions.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            # Use Gemma 3 27B - has vision capabilities and better rate limits
            self.model = genai.GenerativeModel("gemma-3-27b-it")
            logger.info(f"[VISION] VisionAnalyzer initialized with Gemma 3 27B")
        else:
            self.model = None
            logger.warning("[VISION] VisionAnalyzer disabled - no API key or GenAI not available")
    
    def analyze_screen(
        self, 
        screenshot_base64: str, 
        original_goal: str,
        failed_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze screenshot to understand current UI state.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            original_goal: What the user originally wanted to do
            failed_action: The action that failed (if any)
        
        Returns:
            Analysis result with suggested recovery action
        """
        if not self.model:
            return {
                "success": False,
                "error": "Vision analyzer not available"
            }
        
        try:
            # Build task-aware prompt
            prompt = self._build_analysis_prompt(original_goal, failed_action)
            
            # Create image part for Google GenAI
            image_part = {
                "mime_type": "image/png",
                "data": screenshot_base64
            }
            
            # Call Gemma 3 Vision
            response = self.model.generate_content([prompt, image_part])
            
            # Parse response
            result = self._parse_response(response.text)
            result["success"] = True
            
            logger.info(f"[VISION] Analysis: {result.get('current_state', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"[VISION] Analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_analysis_prompt(self, goal: str, failed_action: Optional[str], context_text: str = "") -> str:
        """Build task-aware prompt for vision analysis with execution context."""
        
        prompt = f"""You are an automation recovery vision system with CONTEXTUAL AWARENESS.

{context_text if context_text else f'GOAL: "{goal}"'}
{"VERIFYING: " + failed_action if failed_action else ""}

Analyze this screenshot and determine:
1. What is currently visible on screen?
2. Is the goal being achieved or is something blocking?
3. What is the NEXT action to take?

RESPOND IN JSON ONLY:
{{
  "current_state": "describe what's visible",
  "target_app_visible": true/false,
  "goal_achieved": true/false,
  "blocker": "what's preventing progress (dialog, wrong window, etc.) or null if no blocker",
  "visible_elements": ["list of clickable UI elements with approximate positions"],
  "suggested_action": {{
    "action": "click|type_text|press_key|wait|open_app|none",
    "target": "what to click or type",
    "x": 0,
    "y": 0,
    "content": "text to type if type_text",
    "reasoning": "why this action"
  }},
  "confidence": 0.0-1.0
}}

CRITICAL RULES:
- If goal_achieved is true, set action to "none"
- For CLICK: provide ACTUAL x,y pixel coordinates from the screenshot
- If you see a profile picker (Chrome/Edge), click on a profile
- If a dialog is blocking, close it or click through it
- If focused window doesn't match goal, suggest opening correct app
- Be specific about element positions

JSON ONLY, NO MARKDOWN:"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Groq response into structured data."""
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first and last lines (``` markers)
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            if text.startswith("json"):
                text = text[4:].strip()
            
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"[VISION] Failed to parse JSON: {response_text[:200]}")
            return {
                "current_state": "parse_failed",
                "error": "Failed to parse vision response"
            }
    
    def get_recovery_action(
        self, 
        analysis: Dict[str, Any],
        original_goal: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract actionable recovery step from analysis.
        
        Returns:
            Executor-ready action dict, or None if no recovery possible
        """
        if not analysis.get("success"):
            return None
        
        suggested = analysis.get("suggested_action", {})
        if not suggested:
            return None
        
        confidence = analysis.get("confidence", 0)
        if confidence < 0.5:
            logger.warning(f"[VISION] Low confidence ({confidence}), skipping recovery")
            return None
        
        action = suggested.get("action")
        
        # Build executor action
        recovery = {
            "action": action,
            "reasoning": suggested.get("reasoning", "Vision-based recovery")
        }
        
        if action == "click":
            recovery["x"] = suggested.get("x", 0)
            recovery["y"] = suggested.get("y", 0)
        elif action == "type_text":
            recovery["content"] = suggested.get("target", "")
        elif action == "open_app":
            recovery["target"] = suggested.get("target", "")
        elif action == "press_key":
            recovery["content"] = suggested.get("target", "")
        
        return recovery


# Singleton instance
_vision_analyzer: Optional[VisionAnalyzer] = None


def get_vision_analyzer() -> VisionAnalyzer:
    """Get singleton VisionAnalyzer instance."""
    global _vision_analyzer
    if _vision_analyzer is None:
        _vision_analyzer = VisionAnalyzer()
    return _vision_analyzer


def analyze_screen_for_recovery(
    screenshot_base64: str,
    original_goal: str,
    failed_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze screen and get recovery action.
    
    Args:
        screenshot_base64: Base64 encoded screenshot
        original_goal: What user wanted to achieve
        failed_action: What action failed
    
    Returns:
        Dict with analysis and suggested recovery
    """
    analyzer = get_vision_analyzer()
    analysis = analyzer.analyze_screen(screenshot_base64, original_goal, failed_action)
    
    if analysis.get("success"):
        recovery = analyzer.get_recovery_action(analysis, original_goal)
        analysis["recovery_action"] = recovery
    
    return analysis
