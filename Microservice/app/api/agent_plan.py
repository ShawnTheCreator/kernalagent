"""
Agent Plan API for Desktop Agent Integration.

This provides an HTTP endpoint that the C# Desktop Agent can call
using its existing HTTP polling approach (VoiceToActionService.cs).

Maps user commands to the new v1.0 executor schema.
Supports flexible/fuzzy command matching for typos.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import re
import time
import logging
from datetime import datetime

# ===== STRUCTURED LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("agent")

# ===== KERNEL VOICE PERSONA =====
# System prompt for voice interactions - concise, professional, and proactive
KERNEL_VOICE_PROMPT = """
You are the Kernel Agent voice core. Be concise and professional.

VOICE STYLE:
- Keep responses to 1-2 short sentences
- Never use three words when one will do
- Speak with calm confidence

RESPONSE PATTERNS:
- Acknowledge immediately: "On it. Opening [app]."
- Report progress briefly: "Searching for your template..."
- Confirm completion: "Done. [App] is ready."
- If audio unclear: "Could you repeat that?"
- For dangerous actions: "Delete all files? Say 'yes' to confirm."

PERSONALITY:
- Minimalist and efficient
- Proactive but not chatty
- Calm and capable
"""

def format_voice_response(action: str, target: str = None, success: bool = True) -> str:
    """
    Generate concise voice response for an action.
    These are meant to be spoken by TTS - keep them short!
    """
    if not success:
        return "Something went wrong. Could you try again?"
    
    # Acknowledge patterns
    responses = {
        "open_app": f"Opening {target or 'app'}.",
        "close_app": f"Closing {target or 'app'}.",
        "type_text": "Typing now.",
        "navigate": f"Going to {target or 'page'}.",
        "search_web": f"Searching for {target or 'that'}.",
        "volume_up": "Volume up.",
        "volume_down": "Volume down.",
        "volume_mute": "Muted.",
        "minimize_window": "Minimized.",
        "maximize_window": "Maximized.",
        "screenshot": "Screenshot taken.",
        "copy": "Copied.",
        "paste": "Pasted.",
        "save": "Saved.",
        "media_play_pause": "Playing.",
        "brightness_up": "Brighter.",
        "brightness_down": "Dimmer.",
    }
    
    return responses.get(action, "Done.")


router = APIRouter(prefix="/api/agent", tags=["agent"])


class PlanRequest(BaseModel):
    """Request from C# Desktop Agent."""
    command: str
    session_id: Optional[str] = None
    # NEW: Environment context from C# ContextManager
    context: Optional[Dict[str, Any]] = None  # {active_window, active_app, app_type, clipboard, selected_text, last_action}


class ActionStep(BaseModel):
    """Legacy action format for backward compatibility with C#."""
    action: str
    target: Optional[str] = None
    url: Optional[str] = None
    query: Optional[str] = None
    content: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    label: Optional[str] = None
    amount: Optional[int] = None  # For volume control
    # Vision targeting flag - tells C# this step needs vision to find coordinates
    requires_vision_targeting: Optional[bool] = None
    goal: Optional[str] = None  # For vision_guided steps


class PlanResponse(BaseModel):
    """Response with action steps for C# to execute."""
    session_id: str
    steps: List[ActionStep]
    schema_version: str = "1.0.0"
    # Metadata for debugging and monitoring
    source: Optional[str] = None  # "gemini" or "deterministic"
    processing_time_ms: Optional[int] = None
    timestamp: Optional[str] = None


# App name variations and typo tolerance
APP_ALIASES = {
    # Notepad variations
    "notepad": "notepad.exe", "notpad": "notepad.exe", "note pad": "notepad.exe",
    "notepadd": "notepad.exe", "text editor": "notepad.exe",
    
    # Chrome variations
    "chrome": "chrome.exe", "chrom": "chrome.exe", "crome": "chrome.exe",
    "google chrome": "chrome.exe", "googlechrome": "chrome.exe", "browser": "chrome.exe",
    "web browser": "chrome.exe", "internet": "chrome.exe",
    
    # Edge variations
    "edge": "msedge.exe", "microsoft edge": "msedge.exe", "msedge": "msedge.exe",
    
    # Firefox variations
    "firefox": "firefox.exe", "fire fox": "firefox.exe", "mozila": "firefox.exe",
    "mozilla": "firefox.exe",
    
    # Calculator variations
    "calculator": "calc.exe", "calc": "calc.exe", "calulator": "calc.exe",
    "calculater": "calc.exe", "maths": "calc.exe",
    
    # Explorer variations
    "explorer": "explorer.exe", "file explorer": "explorer.exe", "files": "explorer.exe",
    "file manager": "explorer.exe", "folder": "explorer.exe", "folders": "explorer.exe",
    
    # Office apps
    "word": "winword.exe", "microsoft word": "winword.exe", "ms word": "winword.exe",
    "excel": "excel.exe", "microsoft excel": "excel.exe", "spreadsheet": "excel.exe",
    "powerpoint": "powerpnt.exe", "power point": "powerpnt.exe", "ppt": "powerpnt.exe",
    "outlook": "outlook.exe", "mail": "outlook.exe", "email": "outlook.exe",
    
    # VSCode variations
    "vscode": "code.exe", "vs code": "code.exe", "visual studio code": "code.exe",
    "code": "code.exe", "vsc": "code.exe",
    
    # Terminal variations
    "terminal": "wt.exe", "cmd": "cmd.exe", "command prompt": "cmd.exe",
    "powershell": "powershell.exe", "shell": "wt.exe",
    
    # Other apps
    "paint": "mspaint.exe", "ms paint": "mspaint.exe", "drawing": "mspaint.exe",
    "spotify": "spotify.exe", "music": "spotify.exe",
    "discord": "discord.exe", "teams": "teams.exe", "microsoft teams": "teams.exe",
    "slack": "slack.exe", "zoom": "zoom.exe", "skype": "skype.exe",
    "settings": "ms-settings:", "control panel": "control.exe",
    "task manager": "taskmgr.exe", "taskmanager": "taskmgr.exe",
}


def fuzzy_match(text: str, patterns: list) -> bool:
    """Check if text loosely matches any pattern (typo tolerant)."""
    text = text.lower().strip()
    for pattern in patterns:
        pattern = pattern.lower()
        # Exact match
        if pattern in text:
            return True
        # Check if most characters match (typo tolerance)
        if len(pattern) > 3 and text:
            matches = sum(1 for c in pattern if c in text)
            if matches >= len(pattern) * 0.7:  # 70% match
                return True
    return False


def get_app_exe(app_name: str) -> str:
    """Get executable name for app, with fuzzy matching."""
    app_lower = app_name.lower().strip()
    
    # Direct match
    if app_lower in APP_ALIASES:
        return APP_ALIASES[app_lower]
    
    # Fuzzy match - find best matching alias
    for alias, exe in APP_ALIASES.items():
        if alias in app_lower or app_lower in alias:
            return exe
        # Check character overlap for typos
        if len(app_lower) > 3 and len(alias) > 3:
            matches = sum(1 for c in app_lower if c in alias)
            if matches >= len(app_lower) * 0.7:
                return exe
    
    # Default: append .exe
    return f"{app_lower}.exe"


def parse_command(command: str) -> List[ActionStep]:
    """
    Parse user command into action steps.
    
    Priority order:
    1. Explicit command patterns (open, close, type, search) - checked first
    2. Fuzzy matching for volume/window/system commands
    3. Default fallback
    """
    cmd = command.lower().strip()
    original_cmd = command.strip()  # Keep original for preserving text case
    words = cmd.split()
    original_words = original_cmd.split()
    
    if not words:
        return [ActionStep(action="open_app", target="notepad.exe")]
    
    # ===== EXPLICIT PATTERNS - CHECK FIRST =====
    
    # OPEN APP (highest priority for "open X" commands)
    # Also handles compound commands like "open notepad and type hello"
    open_patterns = ["open", "launch", "start", "run"]
    if words[0] in open_patterns:
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        original_rest = " ".join(original_words[1:]) if len(original_words) > 1 else ""
        
        # Check for compound command: "open X and type Y" (with misspelling tolerance)
        # Handles: "and type", "ant type", "an type", "nd type", "then type", etc.
        compound_keywords = [
            " and type ", " and write ", " then type ", " then write ",
            " ant type ", " an type ", " nd type ",  # Common misspellings
            " ant write ", " an write ", " nd write ",
            " & type ", " + type ",  # Alternate patterns
        ]
        
        # Also try regex for more flexible matching
        import re
        # Match any variation of "and/ant/an/nd" + type/write
        compound_pattern = re.compile(r'\s+(and?t?|an|nd|then|&)\s+(type|write)\s+', re.IGNORECASE)
        compound_match = compound_pattern.search(rest)
        
        if compound_match:
            # Split at the match position - use original_rest to preserve case
            match_start = compound_match.start()
            match_end = compound_match.end()
            app_name = rest[:match_start].strip()
            text_to_type = original_rest[match_end:].strip()  # Preserve original case!
            exe = get_app_exe(app_name)
            logger.info(f"Compound command detected: open '{app_name}' + type '{text_to_type}'")
            return [
                ActionStep(action="open_app", target=exe),
                ActionStep(action="type_text", content=text_to_type)
            ]
        
        # Fallback: exact keyword matching  
        for keyword in compound_keywords:
            if keyword in rest.lower():
                # Find keyword position in lowercased version, extract from original
                keyword_pos = rest.lower().find(keyword)
                app_name = rest[:keyword_pos].strip()
                text_to_type = original_rest[keyword_pos + len(keyword):].strip()  # Preserve case!
                exe = get_app_exe(app_name)
                return [
                    ActionStep(action="open_app", target=exe),
                    ActionStep(action="type_text", content=text_to_type)
                ]
        
        # Check for "open X and search Y"
        search_keywords = [" and search ", " and google ", " then search "]
        for keyword in search_keywords:
            if keyword in rest.lower():
                parts = rest.lower().split(keyword, 1)
                app_name = parts[0].strip()
                query = parts[1].strip()
                exe = get_app_exe(app_name)
                return [
                    ActionStep(action="open_app", target=exe),
                    ActionStep(action="search_web", query=query)
                ]
        
        # Check if it's a URL
        if rest and (rest.startswith("http") or ("." in rest and "/" not in rest[:10])):
            url = rest if rest.startswith("http") else f"https://{rest}"
            return [
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url=url)
            ]
        # It's an app
        if rest:
            exe = get_app_exe(rest)
            return [ActionStep(action="open_app", target=exe)]
        # Just "open" with nothing - default to explorer
        return [ActionStep(action="open_app", target="explorer.exe")]
    
    # CLOSE APP
    close_patterns = ["close", "quit", "exit", "kill", "stop", "end", "terminate"]
    if words[0] in close_patterns:
        app_name = " ".join(words[1:]) if len(words) > 1 else ""
        if app_name:
            exe = get_app_exe(app_name).replace(".exe", "")
            return [ActionStep(action="close_app", target=exe)]
    
    # TYPE TEXT
    type_patterns = ["type", "write", "enter", "input"]
    if words[0] in type_patterns:
        text = " ".join(words[1:]) if len(words) > 1 else ""
        return [ActionStep(action="type_text", content=text)]
    
    # SEARCH
    if cmd.startswith("search for "):
        query = command[11:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    if words[0] in ["search", "google"]:
        query = " ".join(words[1:])
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    
    # NAVIGATE
    nav_patterns = ["go to", "navigate to", "visit", "browse to"]
    for pattern in nav_patterns:
        if cmd.startswith(pattern):
            url = cmd[len(pattern):].strip()
            if not url.startswith("http"):
                url = f"https://{url}"
            return [
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url=url)
            ]
    
    # ===== EXACT MATCH COMMANDS (no fuzzy) =====
    
    # Volume - exact keywords only
    if cmd in ["volume up", "louder", "vol up"]:
        return [ActionStep(action="volume_up", amount=10)]
    if cmd in ["volume down", "quieter", "vol down"]:
        return [ActionStep(action="volume_down", amount=10)]
    if cmd in ["mute", "unmute", "toggle mute"]:
        return [ActionStep(action="volume_mute")]
    if cmd in ["max volume", "full volume"]:
        return [ActionStep(action="volume_set", amount=100)]
    
    # Window - with variations
    if cmd in ["minimize", "minimise", "min", "minimize window", "minimize this window", "minimize this"]:
        return [ActionStep(action="minimize_window")]
    if cmd in ["maximize", "maximise", "max", "fullscreen", "maximize window", "maximize this window", "maximize this"]:
        return [ActionStep(action="maximize_window")]
    if cmd in ["restore", "restore window", "restore this window"]:
        return [ActionStep(action="restore_window")]
    
    # System - exact keywords only
    if cmd in ["lock", "lock screen", "lock computer"]:
        return [ActionStep(action="lock_screen")]
    if cmd in ["sleep", "hibernate"]:
        return [ActionStep(action="sleep")]
    if cmd in ["shutdown", "shut down", "power off"]:
        return [ActionStep(action="shutdown")]
    if cmd in ["restart", "reboot"]:
        return [ActionStep(action="restart")]
    
    # Screenshot
    if cmd in ["screenshot", "screen shot", "take screenshot", "capture screen", "take a screenshot"]:
        return [ActionStep(action="screenshot")]
    
    # ===== VOLUME CONTROL =====
    if cmd in ["volume up", "increase volume", "louder", "turn up volume", "raise volume"]:
        return [ActionStep(action="volume_up", amount=1)]
    if cmd in ["volume down", "decrease volume", "quieter", "turn down volume", "lower volume"]:
        return [ActionStep(action="volume_down", amount=1)]
    if cmd in ["mute", "mute volume", "silence", "turn off sound", "mute audio"]:
        return [ActionStep(action="volume_mute")]
    
    # ===== KEYBOARD SHORTCUTS =====
    # Clipboard
    if cmd in ["copy", "copy this", "copy that"]:
        return [ActionStep(action="copy")]
    if cmd in ["paste", "paste that", "paste it"]:
        return [ActionStep(action="paste")]
    if cmd in ["cut", "cut this", "cut that"]:
        return [ActionStep(action="cut")]
    
    # Undo/Redo
    if cmd in ["undo", "undo that", "go back"]:
        return [ActionStep(action="undo")]
    if cmd in ["redo", "redo that"]:
        return [ActionStep(action="redo")]
    
    # Select/Save
    if cmd in ["select all", "select everything"]:
        return [ActionStep(action="select_all")]
    if cmd in ["save", "save this", "save file", "save document"]:
        return [ActionStep(action="save")]
    
    # Window switching
    if cmd in ["alt tab", "switch window", "next window", "switch windows"]:
        return [ActionStep(action="alt_tab")]
    if cmd in ["show desktop", "go to desktop", "desktop"]:
        return [ActionStep(action="show_desktop")]
    
    # ===== MEDIA CONTROL =====
    if cmd in ["play", "pause", "play pause", "play/pause", "toggle play"]:
        return [ActionStep(action="media_play_pause")]
    if cmd in ["next track", "next song", "skip", "skip song"]:
        return [ActionStep(action="media_next")]
    if cmd in ["previous track", "previous song", "go back song", "last song"]:
        return [ActionStep(action="media_previous")]
    if cmd in ["stop music", "stop media", "stop playing"]:
        return [ActionStep(action="media_stop")]
    
    # ===== BRIGHTNESS =====
    # Using 'in' check for explicit matches + partial matching for flexibility
    brightness_up_phrases = ["brightness up", "increase brightness", "brighter", "raise brightness", "turn up brightness", "screen brighter"]
    brightness_down_phrases = ["brightness down", "decrease brightness", "dimmer", "reduce brightness", "lower brightness", "turn down brightness", "screen dimmer", "dim the screen", "dim screen"]
    
    if cmd in brightness_up_phrases or any(phrase in cmd for phrase in ["brightness up", "brighter", "increase brightness"]):
        return [ActionStep(action="brightness_up", amount=10)]
    if cmd in brightness_down_phrases or any(phrase in cmd for phrase in ["brightness down", "dimmer", "reduce brightness", "lower brightness", "dim"]):
        return [ActionStep(action="brightness_down", amount=10)]
    
    # ===== BROWSER COMMANDS =====
    if cmd in ["new tab", "open new tab", "open tab"]:
        return [ActionStep(action="new_tab")]
    if cmd in ["close tab", "close this tab"]:
        return [ActionStep(action="close_tab")]
    if cmd in ["refresh", "refresh page", "reload", "reload page"]:
        return [ActionStep(action="refresh")]
    if cmd in ["go back", "back", "previous page"]:
        return [ActionStep(action="go_back")]
    if cmd in ["go forward", "forward", "next page"]:
        return [ActionStep(action="go_forward")]
    
    # ===== SCROLL =====
    if cmd in ["scroll up", "scroll page up"]:
        return [ActionStep(action="scroll", target="up")]
    if cmd in ["scroll down", "scroll page down"]:
        return [ActionStep(action="scroll", target="down")]
    
    # ===== HOTKEYS (press ctrl+x format) =====
    if cmd.startswith("press "):
        key = cmd[6:].strip()
        if "+" in key:
            return [ActionStep(action="hotkey", content=key)]
        else:
            return [ActionStep(action="press_key", content=key)]
    
    # Click at coordinates (click 500 300)
    if cmd.startswith("click "):
        parts = cmd[6:].strip().split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return [ActionStep(action="click", x=int(parts[0]), y=int(parts[1]))]
        else:
            return [ActionStep(action="click", target=" ".join(parts))]
    
    # ===== VIRTUAL DESKTOP =====
    if cmd in ["next desktop", "switch desktop right", "desktop right", "right desktop"]:
        return [ActionStep(action="switch_desktop_right")]
    if cmd in ["previous desktop", "switch desktop left", "desktop left", "left desktop", "last desktop"]:
        return [ActionStep(action="switch_desktop_left")]
    if cmd in ["new desktop", "create desktop", "add desktop"]:
        return [ActionStep(action="new_desktop")]
    if cmd in ["close desktop", "remove desktop", "delete desktop"]:
        return [ActionStep(action="close_desktop")]
    if cmd in ["task view", "show desktops", "show all desktops", "desktop view", "view desktops"]:
        return [ActionStep(action="task_view")]
    
    # ===== DEFAULT: Try as app name =====
    exe = get_app_exe(cmd)
    return [ActionStep(action="open_app", target=exe)]


# ===== GEMINI REASONING LAYER INTEGRATION =====
# Gemini is ENABLED by default with improved prompts
# Set GEMINI_ENABLED=false environment variable to disable
import os

_gemini_layer = None
GEMINI_ENABLED = os.environ.get("GEMINI_ENABLED", "true").lower() != "false"

def get_gemini_layer():
    """Lazy initialization of Gemini layer."""
    global _gemini_layer
    
    if not GEMINI_ENABLED:
        return None
    
    if _gemini_layer is None:
        try:
            from app.reasoning import GeminiReasoningLayer
            _gemini_layer = GeminiReasoningLayer(enabled=True)
            print("[AGENT] Gemini layer initialized")
        except Exception as e:
            print(f"[AGENT] Gemini layer init failed: {e}")
            _gemini_layer = None
    return _gemini_layer


async def plan_with_gemini(command: str) -> List[ActionStep]:
    """
    Try to get a plan from Gemini first.
    Falls back to deterministic parsing if Gemini fails or returns nonsense.
    
    Philosophy: "Gemini thinks. Python decides. C# executes."
    """
    cmd_lower = command.lower().strip()
    
    gemini = get_gemini_layer()
    
    if gemini and gemini.enabled:
        try:
            plan = await gemini.plan(command)
            
            if plan:
                # Convert Gemini plan to ActionSteps
                actions = gemini.convert_plan_to_actions(plan)
                
                if actions:
                    first_action = actions[0].get("action", "")
                    
                    # ===== INTENT VALIDATION =====
                    # Check if Gemini's action makes sense for the command
                    is_valid_intent = True
                    
                    # If user says "open X" but action is not open_app, that's wrong
                    if cmd_lower.startswith(("open ", "launch ", "start ", "run ")):
                        if first_action != "open_app":
                            print(f"[AGENT] Intent mismatch: '{cmd_lower}' got '{first_action}'")
                            is_valid_intent = False
                    
                    # If user says "close X" but action is not close_app, that's wrong
                    if cmd_lower.startswith(("close ", "quit ", "exit ", "kill ")):
                        if first_action != "close_app":
                            print(f"[AGENT] Intent mismatch: '{cmd_lower}' got '{first_action}'")
                            is_valid_intent = False
                    
                    # If user says "type X" but action is not type_text, that's wrong
                    if cmd_lower.startswith(("type ", "write ")):
                        if first_action != "type_text":
                            print(f"[AGENT] Intent mismatch: '{cmd_lower}' got '{first_action}'")
                            is_valid_intent = False
                    
                    # If user says brightness-related words but action is not brightness_*, that's wrong
                    brightness_keywords = ["brightness", "brighter", "dimmer", "dim ", "screen dim"]
                    if any(kw in cmd_lower for kw in brightness_keywords):
                        if first_action not in ["brightness_up", "brightness_down"]:
                            print(f"[AGENT] Intent mismatch: brightness command got '{first_action}'")
                            is_valid_intent = False
                    
                    # If user says volume-related words but action is not volume_*, that's wrong
                    volume_keywords = ["volume", "louder", "quieter", "sound", "audio", "mute"]
                    if any(kw in cmd_lower for kw in volume_keywords):
                        if first_action not in ["volume_up", "volume_down", "volume_mute"]:
                            print(f"[AGENT] Intent mismatch: volume command got '{first_action}'")
                            is_valid_intent = False
                    
                    if not is_valid_intent:
                        print(f"[AGENT] Falling back to deterministic due to intent mismatch")
                        return parse_command(command)
                    
                    # ===== END INTENT VALIDATION =====
                    
                    steps = []
                    for action in actions:
                        step = ActionStep(
                            action=action.get("action", ""),
                            target=action.get("target"),
                            url=action.get("url"),
                            query=action.get("query"),
                            content=action.get("content"),
                            amount=action.get("amount")
                        )
                        steps.append(step)
                    
                    print(f"[AGENT] Gemini planned: {len(steps)} steps")
                    return steps
        except Exception as e:
            print(f"[AGENT] Gemini planning failed: {e}")
    
    # ===== GROQ FALLBACK (Llama 3 70B) =====
    try:
        from app.reasoning.groq_fallback import plan_with_groq, GROQ_ENABLED
        if GROQ_ENABLED:
            print(f"[AGENT] Trying Groq fallback...")
            groq_steps = await plan_with_groq(command)
            if groq_steps:
                steps = [
                    ActionStep(
                        action=s.get("action", ""),
                        target=s.get("target"),
                        url=s.get("url"),
                        query=s.get("query"),
                        content=s.get("content"),
                        amount=s.get("amount")
                    )
                    for s in groq_steps
                ]
                print(f"[AGENT] Groq planned: {len(steps)} steps")
                return steps
    except Exception as e:
        print(f"[AGENT] Groq fallback failed: {e}")
    
    # Fallback to deterministic parsing
    logger.warning(f"[AGENT] Using deterministic parsing for: {command}")
    return parse_command(command)


@router.post("/plan", response_model=PlanResponse)
async def get_action_plan(request: PlanRequest):
    """
    Get action plan for a user command.
    
    Uses Gemini for intelligent planning with fallback to deterministic parsing.
    NEW: Also checks for agent matches (e.g., Janitor for cleanup commands).
    
    This endpoint is called by the C# Desktop Agent's VoiceToActionService.
    It parses the user's voice/text command and returns a list of actions.
    
    Example:
        POST /api/agent/plan
        {"command": "open notepad"}
        
        Response:
        {"session_id": "...", "steps": [{"action": "open_app", "target": "notepad.exe"}]}
    """
    session_id = request.session_id or str(uuid.uuid4())
    start_time = time.time()
    source = "deterministic"  # Default, updated if Gemini/Agent succeeds
    
    logger.info(f"📥 Command: '{request.command}'")
    
    try:
        # ===== NEW: Check for Agent Match First =====
        try:
            from app.agents.agent_planner import should_route_to_agent, get_agent_for_intent
            
            agent_name = await should_route_to_agent(request.command)
            if agent_name:
                logger.info(f"🤖 Agent matched: {agent_name}")
                agent = await get_agent_for_intent(request.command)
                
                if agent:
                    # Run agent's analyze -> plan lifecycle
                    context = {"intent": request.command, "session_id": session_id}
                    analysis = await agent.analyze(context)
                    plan = await agent.plan(analysis)
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    # Return agent task step
                    steps = [ActionStep(
                        action="agent_task",
                        target=agent.name,
                        content=f"{len(plan.actions)} cleanup actions ready ({plan.estimated_impact})",
                        label=plan.plan_id,
                    )]
                    
                    logger.info(f"📤 Result: [agent] {agent.name} plan ready ({processing_time}ms)")
                    
                    return PlanResponse(
                        session_id=session_id,
                        steps=steps,
                        schema_version="1.0.0",
                        source=f"agent:{agent.name}",
                        processing_time_ms=processing_time,
                        timestamp=datetime.now().isoformat()
                    )
        except Exception as e:
            logger.warning(f"Agent routing failed: {e}, continuing with Gemini...")
        
        # Try Gemini first, fallback to deterministic
        steps = await plan_with_gemini(request.command)
        
        # Determine source based on steps (Gemini sets internal flag)
        gemini = get_gemini_layer()
        if gemini and gemini.enabled:
            source = "gemini"  # Attempted Gemini
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log result
        action_summary = ", ".join([s.action for s in steps[:3]])
        logger.info(f"📤 Result: [{source}] {len(steps)} step(s): {action_summary} ({processing_time}ms)")
        
        return PlanResponse(
            session_id=session_id,
            steps=steps,
            schema_version="1.0.0",
            source=source,
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/gemini", response_model=PlanResponse)
async def get_gemini_plan(request: PlanRequest):
    """
    Get action plan using Gemini ONLY (no fallback).
    Useful for testing Gemini integration.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    gemini = get_gemini_layer()
    
    if not gemini or not gemini.enabled:
        raise HTTPException(status_code=503, detail="Gemini not available")
    
    plan = await gemini.plan(request.command)
    
    if not plan:
        raise HTTPException(status_code=422, detail="Gemini could not create a plan")
    
    actions = gemini.convert_plan_to_actions(plan)
    steps = [
        ActionStep(
            action=a.get("action", ""),
            target=a.get("target"),
            url=a.get("url"),
            query=a.get("query"),
            content=a.get("content"),
            amount=a.get("amount")
        )
        for a in actions
    ]
    
    return PlanResponse(
        session_id=session_id,
        steps=steps,
        schema_version="1.0.0"
    )


@router.get("/health")
async def agent_health():
    """Health check for agent API."""
    gemini = get_gemini_layer()
    
    gemini_info = {
        "enabled": False,
        "status": "disabled"
    }
    
    if gemini:
        gemini_info["enabled"] = gemini.enabled
        if gemini.enabled:
            # Check rate limit status
            import time
            from app.reasoning.gemini_layer import GeminiReasoningLayer
            
            if time.time() < GeminiReasoningLayer._rate_limit_until:
                wait_time = int(GeminiReasoningLayer._rate_limit_until - time.time())
                gemini_info["status"] = f"rate_limited ({wait_time}s remaining)"
            else:
                gemini_info["status"] = "ready"
            
            gemini_info["consecutive_failures"] = GeminiReasoningLayer._consecutive_failures
        else:
            gemini_info["status"] = "disabled"
    
    return {
        "status": "ready", 
        "version": "1.0.0",
        "gemini": gemini_info,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status")
async def agent_status():
    """Detailed status endpoint for monitoring."""
    gemini = get_gemini_layer()
    
    return {
        "api": "ready",
        "gemini_enabled": GEMINI_ENABLED,
        "gemini_initialized": gemini is not None and gemini.enabled,
        "supported_actions": [
            "open_app", "close_app", "type_text", "navigate", "search_web",
            "volume_up", "volume_down", "volume_mute",
            "minimize_window", "maximize_window", "restore_window",
            "copy", "paste", "cut", "undo", "redo", "select_all", "save",
            "alt_tab", "show_desktop", "press_key", "hotkey",
            "media_play_pause", "media_next", "media_previous", "media_stop",
            "new_tab", "close_tab", "refresh", "go_back", "go_forward",
            "click", "double_click", "right_click", "scroll",
            "brightness_up", "brightness_down",
            "lock_screen", "sleep", "shutdown", "restart", "screenshot"
        ],
        "version": "1.0.0"
    }


# ===== LLM-FIRST ARCHITECTURE (v2) =====

@router.post("/plan/v2", response_model=PlanResponse)
async def get_action_plan_v2(request: PlanRequest):
    """
    Get action plan using LLM-First Architecture (v2).
    
    This endpoint uses the new Intent → Plan → Execute pipeline:
    1. Intent Analyzer (LLM) extracts structured intent
    2. Tool Registry maps to executor actions
    3. Context Memory enables "do that again" support
    
    Falls back to deterministic parser if LLM fails.
    """
    session_id = request.session_id or str(uuid.uuid4())
    start_time = time.time()
    source = "llm_first"
    
    logger.info(f"📥 [v2] Command: '{request.command}'")
    
    try:
        from app.reasoning.llm_planner import plan_command_with_fallback
        
        # Use the new LLM-first planner
        step_dicts = await plan_command_with_fallback(request.command, session_id)
        
        # DEBUG: Log full step_dicts 
        logger.info(f"[DEBUG] Planner returned {len(step_dicts)} steps:")
        for i, s in enumerate(step_dicts, 1):
            logger.info(f"[DEBUG]   {i}. {s.get('action')} - content:{s.get('content')}")
        
        # Convert to ActionStep objects
        steps = [
            ActionStep(
                action=s.get("action", ""),
                target=s.get("target"),
                url=s.get("url"),
                query=s.get("query"),
                content=s.get("content"),
                amount=s.get("amount"),
                x=s.get("x"),
                y=s.get("y"),
                requires_vision_targeting=s.get("requires_vision_targeting"),
                goal=s.get("goal"),
            )
            for s in step_dicts
        ]
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log result
        action_summary = ", ".join([s.action for s in steps[:3]])
        logger.info(f"📤 [v2] Result: {len(steps)} step(s): {action_summary} ({processing_time}ms)")
        
        return PlanResponse(
            session_id=session_id,
            steps=steps,
            schema_version="2.0.0",
            source=source,
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"❌ [v2] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ===== VISION-BASED RECOVERY (v3) =====

class RecoveryRequest(BaseModel):
    """Request for vision-based recovery with execution context."""
    original_command: str
    failed_action: str
    error_reason: Optional[str] = "unknown"
    session_id: Optional[str] = None
    # Context from C# executor
    focused_window: Optional[str] = None
    focused_process: Optional[str] = None
    opened_apps: Optional[List[str]] = None
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    last_action: Optional[str] = None
    last_result: Optional[bool] = None


class RecoveryResponse(BaseModel):
    """Response from vision recovery."""
    success: bool
    recovery_possible: bool
    recovery_action: Optional[Dict[str, Any]] = None
    current_state: Optional[str] = None
    blocker: Optional[str] = None
    confidence: Optional[float] = None
    message: Optional[str] = None


@router.post("/recover")
async def attempt_vision_recovery(request: RecoveryRequest) -> RecoveryResponse:
    """
    Attempt vision-based recovery when an action fails.
    
    Flow:
    1. Capture screenshot of current screen
    2. Analyze with Gemini Vision
    3. Determine what's blocking progress
    4. Suggest recovery action
    
    Call this when C# executor fails on an action.
    """
    logger.info(f"🔍 [RECOVERY] Request for: '{request.original_command}'")
    logger.info(f"🔍 [RECOVERY] Failed action: {request.failed_action}")
    if request.focused_window:
        logger.info(f"🔍 [RECOVERY] Focused: {request.focused_window}")
    
    try:
        from app.vision.recovery_planner import attempt_recovery, get_execution_context
        
        # Populate execution context from request
        ctx = get_execution_context()
        ctx.original_goal = request.original_command
        ctx.focused_window = request.focused_window or ""
        ctx.focused_process = request.focused_process or ""
        ctx.opened_apps = request.opened_apps or []
        ctx.current_step = request.step_number or 0
        ctx.total_steps = request.total_steps or 0
        ctx.last_action = request.last_action or ""
        if request.last_result is not None:
            ctx.last_result = request.last_result
        
        result = attempt_recovery(
            original_goal=request.original_command,
            failed_action=request.failed_action,
            error_reason=request.error_reason or "unknown"
        )
        
        # BIDIRECTIONAL: Feed Vision observations back to LLM context
        if result.get("success") and result.get("current_state"):
            from app.memory.context import get_session
            session = get_session(request.session_id or "default")
            session.add_vision_observation(result.get("current_state", ""))
            if request.focused_window:
                session.update_focused_window(
                    request.focused_window or "",
                    request.focused_process or ""
                )
            logger.info(f"[RECOVERY] Vision→LLM: {result.get('current_state')}")
        
        if result.get("success"):
            logger.info(f"✅ [RECOVERY] Suggested: {result.get('recovery_action', {}).get('action')}")
        else:
            logger.warning(f"⚠️ [RECOVERY] Failed: {result.get('message')}")
        
        return RecoveryResponse(
            success=result.get("success", False),
            recovery_possible=result.get("recovery_possible", False),
            recovery_action=result.get("recovery_action"),
            current_state=result.get("current_state"),
            blocker=result.get("blocker"),
            confidence=result.get("confidence"),
            message=result.get("message")
        )
    except Exception as e:
        logger.error(f"❌ [RECOVERY] Error: {e}")
        import traceback
        traceback.print_exc()
        return RecoveryResponse(
            success=False,
            recovery_possible=False,
            message=str(e)
            )

