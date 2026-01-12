"""
Vision Engine for Kernal Agent AI Brain.

Handles screenshot analysis using Gemini Vision API.
Now integrated with Agent Decision Engine for intelligent skill reuse.

Flow: Vision Signal → Decision Engine → Gemini → Action JSON
"""
import base64
import io
import json
import time
import random
from PIL import Image
from typing import Optional

from google.genai import types

from app.core.config import client, MODEL_ID
from app.core.schemas import KernalAction
from app.agent.decision_engine import decide_next_action, get_decision_for_gemini
from app.agent.failure_detector import detect_failure, calculate_adjusted_confidence
from app.agent.memory import AgentMemory


# Vision signal detection (simplified - in production would use CLIP)
def detect_vision_signal(current_image: Image.Image, previous_image: Optional[Image.Image] = None) -> str:
    """
    Detect the current vision signal state.
    
    For hackathon: Returns UI_STABLE by default.
    In production: Would compare current vs previous frame using CLIP.
    
    Returns:
        One of: SCREEN_CHANGED, LAYOUT_CHANGE, MINOR_UPDATE, UI_STABLE
    """
    # Placeholder - in production would use CLIP similarity
    if previous_image is None:
        return "UI_STABLE"
    
    # Simple size comparison as placeholder
    if current_image.size != previous_image.size:
        return "SCREEN_CHANGED"
    
    return "UI_STABLE"


def call_gemini_with_retry(
    model_id: str, 
    prompt: str, 
    image: Image.Image, 
    retries: int = 3
):
    """
    Calls Gemini API with exponential backoff retry on rate limits.
    
    Args:
        model_id: The Gemini model to use
        prompt: The text prompt
        image: PIL Image object
        retries: Number of retry attempts
        
    Returns:
        Gemini response object or None on failure
    """
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=KernalAction
                )
            )
            return response
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate Limit hit. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"API Error: {e}")
                return None
            
    print("Max retries reached. Gemini is busy.")
    return None


def analyze_frame(
    base64_image: str, 
    user_intent: str,
    previous_action: Optional[dict] = None,
    previous_image: Optional[str] = None,
<<<<<<< HEAD
    session_id: Optional[str] = None
=======
    memory: Optional[AgentMemory] = None
>>>>>>> 075af4c8af26a65bd380c3f04c26ccead1e287a8
) -> dict:
    """
    Analyzes a screenshot and returns the next action to take.
    
    NEW FLOW:
    1. Detect vision signal
    2. Get decision from Decision Engine (chooses strategy)
    3. Build context-aware prompt for Gemini
    4. Let Gemini explain and generate action
    5. Enforce standardized output format
    
    Args:
        base64_image: Base64 encoded screenshot
        user_intent: What the user wants to accomplish
        previous_action: The last action taken (for failure detection)
        previous_image: Previous frame for signal detection
        
    Returns:
        Dictionary containing the action plan with confidence and strategy
    """
    try:
        # Step 1: Decode the Base64 image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))

        # Resize large images to reduce token usage
        if image.width > 1024:
            aspect_ratio = image.height / image.width
            new_height = int(1024 * aspect_ratio)
            image = image.resize((1024, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Step 2: Detect vision signal
        prev_image = None
        if previous_image:
            try:
                prev_data = base64.b64decode(previous_image)
                prev_image = Image.open(io.BytesIO(prev_data))
            except:
                pass
        
        vision_signal = detect_vision_signal(image, prev_image)
        print(f"[VISION] Signal: {vision_signal}")
        
        # Step 3: Get decision from Decision Engine (now with STM)
        decision = decide_next_action(
            vision_signal=vision_signal,
            user_intent=user_intent,
            last_action=previous_action,
<<<<<<< HEAD
            session_id=session_id
=======
            memory=memory
>>>>>>> 075af4c8af26a65bd380c3f04c26ccead1e287a8
        )
        print(f"[DECISION] Strategy: {decision['strategy']} | Confidence: {decision['confidence']:.0%}")
        
        # Log memory context if available
        if memory:
            print(memory.format_for_log())
        
        # Step 4: Check for previous action failure
        failure_result = None
        if previous_action:
            expected_signal = previous_action.get('expected_signal')
            failure_result = detect_failure(
                action_type=previous_action.get('action_type', 'WAIT'),
                expected_signal=expected_signal,
                actual_signal=vision_signal
            )
            if failure_result.get('failed'):
                print(f"[FAILURE] {failure_result.get('reason')}")
                # Record failure in STM
                if memory:
                    memory.record_failure()
                    print(f"[STM] Recorded failure (count: {memory.failure_count})")
                decision['confidence'] = calculate_adjusted_confidence(
                    decision['confidence'],
                    [],  # Would track history in production
                    failure_result
                )
            else:
                # Record success in STM (resets failure count)
                if memory:
                    memory.record_success()
        
        # Build memory context string for prompt
        memory_context_str = ""
        if memory:
            ctx = memory.get_context()
            memory_context_str = f"""
MEMORY CONTEXT:
- Last Action: {ctx['last_action']}
- Last Skill: {ctx['last_skill']}
- Failures: {ctx['failure_count']}
"""
        
        # Step 5: Build prompt with decision context
        decision_context = get_decision_for_gemini(decision)
        
        prompt = f"""
You are Kernal, an intelligent desktop agent.
The user wants to: "{user_intent}"

{decision_context}

CURRENT CONTEXT:
- Vision Signal: {vision_signal}
- Confidence Level: {decision['confidence']:.0%}
- Reason: {decision['reason']}
{memory_context_str}
Look at the screenshot carefully.
If specific UI elements have red number tags, use 'coordinate_label' to identify them.
If no tags are present, describe what should be clicked.

Return the SINGLE next immediate step to take.
Be precise. Do not explain multiple steps.
"""

        # Step 6: Call Gemini
        response = call_gemini_with_retry(MODEL_ID, prompt, image)

        if response and response.text:
            result = json.loads(response.text)
            
            # Step 7: Enforce standardized output format
            standardized_result = {
                "explanation": result.get("explanation", "Action determined by agent"),
                "action_type": result.get("action_type", "WAIT"),
                "coordinate_label": result.get("coordinate_label"),
                "text_payload": result.get("text_payload"),
                "confidence": decision['confidence'],
                "strategy": decision['strategy'],
                "skill_id": decision.get('skill_id')
            }
            
            # Add expected signal for next frame's failure detection
            expected_signals = {
                "CLICK": "SCREEN_CHANGED",
                "TYPE": "MINOR_UPDATE",
                "SCROLL": "LAYOUT_CHANGE",
                "WAIT": "UI_STABLE",
                "DONE": "UI_STABLE"
            }
            standardized_result["expected_signal"] = expected_signals.get(
                standardized_result["action_type"], 
                "UI_STABLE"
            )
            
            # Step 8: Record action in STM
            if memory:
                memory.record_action(
                    action_type=standardized_result["action_type"],
                    skill_name=decision.get('skill_name'),
                    signal=vision_signal
                )
                # Add memory context to output for explainability
                standardized_result["memory_context"] = memory.get_context()
            
            return standardized_result
        else:
            return {
                "error": "Failed to get response from Brain",
                "confidence": 0.0,
                "strategy": "FRESH_REASONING"
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Vision Error: {e}")
        return {
            "error": str(e),
            "confidence": 0.0,
            "strategy": "FRESH_REASONING"
        }
