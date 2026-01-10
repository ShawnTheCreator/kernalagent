"""
Vision Engine for Kernal Agent AI Brain.
Handles screenshot analysis using Gemini Vision API.
"""
import base64
import io
import json
import time
import random
from PIL import Image

from google.genai import types

from app.core.config import client, MODEL_ID
from app.core.schemas import KernalAction


def call_gemini_with_retry(model_id: str, prompt: str, image: Image.Image, retries: int = 3):
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


def analyze_frame(base64_image: str, user_intent: str) -> dict:
    """
    Analyzes a screenshot and returns the next action to take.
    
    Args:
        base64_image: Base64 encoded screenshot
        user_intent: What the user wants to accomplish
        
    Returns:
        Dictionary containing the action plan or an error
    """
    try:
        # Decode the Base64 image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))

        # Resize large images to reduce token usage
        if image.width > 1024:
            aspect_ratio = image.height / image.width
            new_height = int(1024 * aspect_ratio)
            image = image.resize((1024, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed (remove alpha channel)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        prompt = f"""
        You are Kernal, a native desktop agent.
        The user wants to: "{user_intent}"
        
        Look at the screenshot. 
        If specific UI elements have red number tags, use 'coordinate_label' to identify them.
        If no tags are present, explain what should be clicked.
        
        Return the next immediate step to take.       
        """

        response = call_gemini_with_retry(MODEL_ID, prompt, image)

        if response and response.text:
            return json.loads(response.text)
        else:
            return {"error": "Failed to get response from Brain"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Vision Error: {e}")
        return {"error": str(e)}
