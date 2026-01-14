"""
Agent Plan API for Desktop Agent Integration.

This provides an HTTP endpoint that the C# Desktop Agent can call
using its existing HTTP polling approach (VoiceToActionService.cs).

Maps user commands to the new v1.0 executor schema.
Supports flexible/fuzzy command matching for typos.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
import re

router = APIRouter(prefix="/api/agent", tags=["agent"])


class PlanRequest(BaseModel):
    """Request from C# Desktop Agent."""
    command: str
    session_id: Optional[str] = None


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


class PlanResponse(BaseModel):
    """Response with action steps for C# to execute."""
    session_id: str
    steps: List[ActionStep]
    schema_version: str = "1.0.0"


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
    
    Supports flexible matching with typos:
    - "open X" / "launch X" / "start X" - Opens an application
    - "close X" / "quit X" / "exit X" / "kill X" - Closes an application
    - "type X" / "write X" - Types text
    - "search X" / "google X" - Searches for something
    - "go to X" / "navigate X" / "open X" (URL) - Navigates to URL
    - "volume up/down/mute" - Volume control
    - "minimize/maximize/restore" - Window management
    - "lock" / "sleep" / "shutdown" - System commands
    """
    cmd = command.lower().strip()
    words = cmd.split()
    
    # ===== CLOSE APP =====
    close_patterns = ["close", "quit", "exit", "kill", "stop", "end", "terminate"]
    if words and words[0] in close_patterns:
        app_name = " ".join(words[1:]) if len(words) > 1 else ""
        if app_name:
            exe = get_app_exe(app_name).replace(".exe", "")
            return [ActionStep(action="close_app", target=exe)]
    
    # ===== VOLUME CONTROL =====
    if fuzzy_match(cmd, ["volume up", "turn up volume", "louder", "increase volume", "vol up"]):
        return [ActionStep(action="volume_up", amount=10)]
    if fuzzy_match(cmd, ["volume down", "turn down volume", "quieter", "decrease volume", "vol down", "lower volume"]):
        return [ActionStep(action="volume_down", amount=10)]
    if fuzzy_match(cmd, ["mute", "unmute", "toggle mute", "silence"]):
        return [ActionStep(action="volume_mute")]
    if fuzzy_match(cmd, ["max volume", "full volume", "maximum volume"]):
        return [ActionStep(action="volume_set", amount=100)]
    
    # ===== WINDOW MANAGEMENT =====
    if fuzzy_match(cmd, ["minimize", "minimise", "min window"]):
        return [ActionStep(action="minimize_window")]
    if fuzzy_match(cmd, ["maximize", "maximise", "max window", "fullscreen"]):
        return [ActionStep(action="maximize_window")]
    if fuzzy_match(cmd, ["restore window", "restore"]):
        return [ActionStep(action="restore_window")]
    
    # ===== SYSTEM COMMANDS =====
    if fuzzy_match(cmd, ["lock", "lock screen", "lock computer", "lock pc"]):
        return [ActionStep(action="lock_screen")]
    if fuzzy_match(cmd, ["sleep", "hibernate", "sleep mode"]):
        return [ActionStep(action="sleep")]
    if fuzzy_match(cmd, ["shutdown", "shut down", "power off", "turn off"]):
        return [ActionStep(action="shutdown")]
    if fuzzy_match(cmd, ["restart", "reboot"]):
        return [ActionStep(action="restart")]
    
    # ===== SCREENSHOT =====
    if fuzzy_match(cmd, ["screenshot", "screen shot", "capture screen", "print screen", "take screenshot"]):
        return [ActionStep(action="screenshot")]
    
    # ===== OPEN APP =====
    open_patterns = ["open", "launch", "start", "run"]
    if words and words[0] in open_patterns:
        rest = " ".join(words[1:])
        # Check if it's a URL
        if rest.startswith("http") or "." in rest and "/" not in rest[:10]:
            url = rest if rest.startswith("http") else f"https://{rest}"
            return [
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url=url)
            ]
        # It's an app
        if rest:
            exe = get_app_exe(rest)
            return [ActionStep(action="open_app", target=exe)]
    
    # ===== TYPE TEXT =====
    type_patterns = ["type", "write", "enter", "input"]
    if words and words[0] in type_patterns:
        text = " ".join(words[1:])
        return [ActionStep(action="type_text", content=text)]
    
    # ===== SEARCH =====
    if cmd.startswith("search for "):
        query = command[11:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    if cmd.startswith("search ") or cmd.startswith("google "):
        query = " ".join(words[1:])
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    
    # ===== NAVIGATE =====
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
    
    # ===== CLICK (placeholder) =====
    if cmd.startswith("click "):
        target = command[6:].strip()
        return [ActionStep(action="click", target=target)]
    
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
    
    # Fallback to deterministic parsing
    print(f"[AGENT] Using deterministic parsing")
    return parse_command(command)


@router.post("/plan", response_model=PlanResponse)
async def get_action_plan(request: PlanRequest):
    """
    Get action plan for a user command.
    
    Uses Gemini for intelligent planning with fallback to deterministic parsing.
    
    This endpoint is called by the C# Desktop Agent's VoiceToActionService.
    It parses the user's voice/text command and returns a list of actions.
    
    Example:
        POST /api/agent/plan
        {"command": "open notepad"}
        
        Response:
        {"session_id": "...", "steps": [{"action": "open_app", "target": "notepad.exe"}]}
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Try Gemini first, fallback to deterministic
        steps = await plan_with_gemini(request.command)
        
        return PlanResponse(
            session_id=session_id,
            steps=steps,
            schema_version="1.0.0"
        )
    except Exception as e:
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
    gemini_status = "enabled" if (gemini and gemini.enabled) else "disabled"
    
    return {
        "status": "ready", 
        "version": "1.0.0",
        "gemini": gemini_status
    }


