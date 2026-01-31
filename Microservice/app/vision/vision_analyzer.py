"""
Vision Analyzer - Gemini Vision for UI Understanding

Analyzes screenshots to understand UI state and suggest recovery actions.
Uses task-aware prompting for accurate perception.
Uses Google's Gemini vision model via google-genai SDK.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file (check parent dir too)
env_path = Path(__file__).parent.parent.parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)

DISABLE_GEMINI_VISION = True

# Import Google GenAI SDK (same as intent_analyzer)
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("Google GenAI SDK not available - vision analysis disabled")


class VisionAnalyzer:
    """
    Analyzes screenshots using Gemini Vision to understand UI state
    and suggest recovery actions.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = None
        
        logger.info(f"[VISION] GENAI_AVAILABLE = {GENAI_AVAILABLE}")
        logger.info(f"[VISION] API key present = {bool(self.api_key)}")
        logger.info(f"[VISION] DISABLE_GEMINI_VISION = {DISABLE_GEMINI_VISION}")
        
        if DISABLE_GEMINI_VISION:
            logger.warning("[VISION] Gemini Vision is disabled by DISABLE_GEMINI_VISION=true")
            self.client = None
        elif self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client()
                logger.info(f"[VISION] VisionAnalyzer initialized with Gemini")
            except Exception as e:
                logger.error(f"[VISION] GenAI client init failed: {e}")
                self.client = None
        else:
            logger.warning("[VISION] VisionAnalyzer disabled - no API key or GenAI not available")
    
    def analyze_screen(
        self, 
        screenshot_base64: str, 
        original_goal: str,
        failed_action: Optional[str] = None,
        context_text: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze screenshot to understand current UI state.
        Includes retry logic for 429/503 errors.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            original_goal: What the user originally wanted to do
            failed_action: The action that failed (if any)
        
        Returns:
            Analysis result with suggested recovery action
        """
        if not self.client:
            return {
                "success": False,
                "error": "Vision analyzer not available"
            }
        
        # Build task-aware prompt
        prompt = self._build_analysis_prompt(original_goal, failed_action, context_text=context_text)
        
        # Retry logic for API rate limits
        import time
        from app.core.retry import is_retryable_error
        
        # Get model from environment
        vision_model = os.getenv("VISION_MODEL", "gemma-3-27b-it")
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Call Gemini Vision using new SDK
                response = self.client.models.generate_content(
                    model=vision_model,
                    contents=[
                        {"role": "user", "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": screenshot_base64}}
                        ]}
                    ],
                    config={"temperature": 0.2, "max_output_tokens": 1024}
                )
                
                # Parse response
                result = self._parse_response(response.text)
                result["success"] = True
                
                if attempt > 0:
                    logger.info(f"[VISION] Succeeded on retry {attempt}")
                
                logger.info(f"[VISION] Analysis: {result.get('current_state', 'unknown')}")
                return result
                
            except Exception as e:
                last_error = e
                is_retryable, suggested_delay = is_retryable_error(e)
                
                if not is_retryable or attempt >= max_retries:
                    logger.error(f"[VISION] Analysis failed after {attempt + 1} attempts: {e}")
                    return {
                        "success": False,
                        "error": str(e)
                    }
                
                delay = min(2.0 * (2 ** attempt), 30.0)
                if suggested_delay and suggested_delay > delay:
                    delay = min(suggested_delay, 30.0)
                
                logger.warning(f"[VISION] Attempt {attempt + 1} failed. Retrying in {delay:.1f}s...")
                time.sleep(delay)
        
        return {
            "success": False,
            "error": str(last_error) if last_error else "Unknown error"
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
            recovery["content"] = suggested.get("content") or suggested.get("target", "")
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
