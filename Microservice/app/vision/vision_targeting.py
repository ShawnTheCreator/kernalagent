"""
Vision Targeting - Find clickable elements when target is ambiguous.

Called when a step has requires_vision_targeting=True.
Uses Gemini/Gemma Vision to find specific UI elements like video thumbnails.
Includes exponential backoff retry for API rate limits.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def find_click_target(
    screenshot_base64: str,
    target_description: str,
    goal_context: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Use vision to find a clickable target with OpenCV/EasyOCR fallback to Gemini.
    
    Args:
        screenshot_base64: Base64 encoded screenshot
        target_description: What to find (e.g., "any video", "first result")
        goal_context: Optional context about what user is trying to do
    
    Returns:
        {"x": int, "y": int, "confidence": float, "element": str} or None
    """
    # Try OpenCV/EasyOCR first for UI elements
    try:
        from app.vision.opencv_detector import find_click_target_opencv
        opencv_result = find_click_target_opencv(screenshot_base64, target_description)
        if opencv_result:
            logger.info(f"[TARGETING] OpenCV found '{target_description}' at ({opencv_result['x']}, {opencv_result['y']})")
            return opencv_result
    except Exception as e:
        logger.warning(f"[TARGETING] OpenCV detection failed: {e}")

    # Fallback to Gemini vision
    from app.vision.vision_analyzer import get_vision_analyzer
    from app.core.retry import retry_with_backoff
    
    analyzer = get_vision_analyzer()
    if not analyzer.client:
        logger.error("[TARGETING] Vision analyzer not available")
        return None
    
    # Build specialized prompt for target finding
    prompt = _build_targeting_prompt(target_description, goal_context)
    
    # Get model from environment
    import os
    vision_model = os.getenv("VISION_MODEL", "gemma-3-27b-it")
    
    async def _call_vision():
        """Inner function for retry wrapper."""
        response = analyzer.client.models.generate_content(
            model=vision_model,
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": screenshot_base64}}
                ]}
            ],
            config={"temperature": 0.2, "max_output_tokens": 512}
        )
        
        if response and response.text:
            result = _parse_targeting_response(response.text)
            
            if result and result.get("found"):
                logger.info(f"[TARGETING] Gemini found '{target_description}' at ({result['x']}, {result['y']})")
                result["method"] = "gemini"
                return result
            else:
                logger.warning(f"[TARGETING] Gemini could not find: {target_description}")
                return None
        return None
    
    try:
        # Use retry with exponential backoff for 429/503 errors
        return await retry_with_backoff(
            _call_vision,
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0
        )
    except Exception as e:
        logger.error(f"[TARGETING] Gemini error after retries: {e}")
        return None


def _build_targeting_prompt(target: str, goal: str = "") -> str:
    """Build specialized prompt for finding click targets."""
    
    return f"""You are a UI automation vision system analyzing a screenshot to find clickable elements.

TARGET TO FIND: "{target}"
{f'USER GOAL: {goal}' if goal else ''}

IMPORTANT: This screenshot is from a high-resolution display (likely 1920x1080 or similar).
Coordinates should reflect ACTUAL pixel positions in the image, not normalized values.

TASK: Find the CENTER pixel coordinates of the BEST matching element.

WHAT TO LOOK FOR:
- For "any video" / "first video" on YouTube → Look for the FIRST video thumbnail (large rectangular image with title below). On YouTube homepage, first video is typically around x=300-500, y=300-500.
- For "first result" / "top result" → Look for the first clickable search result
- For "play button" → Look for triangular play icons or buttons labeled "Play"
- For "search box" → Look for text input fields, often with magnifying glass icon

Return ONLY valid JSON (no markdown, no code blocks):
{{"found": true, "x": 450, "y": 380, "element": "Video thumbnail: Example Title", "confidence": 0.9}}

OR if not found:
{{"found": false, "reason": "No video thumbnails visible on screen"}}

CRITICAL RULES:
1. Return ACTUAL pixel coordinates based on where elements appear in this screenshot
2. For YouTube videos: thumbnails are usually in the CENTER-LEFT area (x: 200-600, y: 300-600)
3. Pick the CENTER of the clickable thumbnail image, not the title text
4. Coordinates must be realistic for a 1920x1080 screen - NOT low values like (50,50) or (240,240)
5. Look carefully at the screenshot and identify the exact position"""


def _parse_targeting_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse vision model response into coordinates."""
    import json
    
    try:
        # Clean up response
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)
        
        if text.startswith("json"):
            text = text[4:].strip()
        
        result = json.loads(text)
        
        # Validate result
        if result.get("found"):
            x = result.get("x")
            y = result.get("y")
            
            if x is not None and y is not None and x > 0 and y > 0:
                return {
                    "found": True,
                    "x": int(x),
                    "y": int(y),
                    "element": result.get("element", "unknown"),
                    "confidence": result.get("confidence", 0.5)
                }
        
        return {"found": False, "reason": result.get("reason", "Unknown")}
        
    except json.JSONDecodeError as e:
        logger.error(f"[TARGETING] JSON parse error: {e}")
        logger.error(f"[TARGETING] Raw response: {response_text[:200]}")
        return None
