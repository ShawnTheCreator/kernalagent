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

    logger.info(f"[TARGETING] No OpenCV match for '{target_description}'. Returning None (no Gemini fallback).")
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
