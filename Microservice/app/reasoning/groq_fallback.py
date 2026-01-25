# Groq Fallback Layer for Desktop Automation
# Uses Llama 3 70B for intelligent command planning when Gemini is unavailable

import os
import json
from typing import Dict, Any, Optional, List

# Groq API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_ENABLED = bool(GROQ_API_KEY)

# Groq client (lazy init)
_groq_client = None

def get_groq_client():
    """Get or create Groq client."""
    global _groq_client
    if _groq_client is None and GROQ_ENABLED:
        try:
            from groq import Groq
            _groq_client = Groq(api_key=GROQ_API_KEY)
            print("[GROQ] Client initialized successfully")
        except ImportError:
            print("[GROQ] groq package not installed. Run: pip install groq")
        except Exception as e:
            print(f"[GROQ] Failed to initialize: {e}")
    return _groq_client


GROQ_SYSTEM_PROMPT = """You are a desktop automation assistant. Convert user commands into structured action plans.

Available actions:
- open_app: Open an application (target = exe name like "notepad.exe")
- close_app: Close an application
- type_text: Type text (content = text to type)
- volume_up, volume_down, volume_mute: Control volume
- copy, paste, cut, undo, redo, select_all, save: Keyboard shortcuts
- media_play_pause, media_next, media_previous: Media control
- new_tab, close_tab, refresh, go_back, go_forward: Browser control
- navigate: Go to URL (url = the URL)
- search_web: Search (query = search terms)
- screenshot: Take screenshot

RESPOND ONLY WITH JSON. No explanations.
Format: {"steps": [{"action": "action_name", "target": "optional", "content": "optional", "url": "optional"}]}

Examples:
User: "open notepad"
{"steps": [{"action": "open_app", "target": "notepad.exe"}]}

User: "increase volume"
{"steps": [{"action": "volume_up"}]}

User: "open chrome and go to youtube"
{"steps": [{"action": "open_app", "target": "chrome.exe"}, {"action": "navigate", "url": "https://youtube.com"}]}
"""


async def plan_with_groq(command: str) -> Optional[List[Dict[str, Any]]]:
    """
    Generate action plan using Groq's Llama 3 model.
    Returns list of action dicts or None on failure.
    """
    client = get_groq_client()
    if not client:
        return None
    
    try:
        print(f"[GROQ] Planning: '{command}'")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Fast and capable
            messages=[
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": command}
            ],
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        print(f"[GROQ] Response: {result_text[:200]}")
        
        # Parse JSON
        result = json.loads(result_text)
        steps = result.get("steps", [])
        
        if steps:
            print(f"[GROQ] Planned {len(steps)} step(s)")
            return steps
        
        return None
        
    except Exception as e:
        print(f"[GROQ] Error: {e}")
        return None
