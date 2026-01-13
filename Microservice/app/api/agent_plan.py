"""
Agent Plan API for Desktop Agent Integration.

This provides an HTTP endpoint that the C# Desktop Agent can call
using its existing HTTP polling approach (VoiceToActionService.cs).

Maps user commands to the new v1.0 executor schema.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.executor import CommandGenerator, Target, Command, ActionType

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
    label: Optional[int] = None


class PlanResponse(BaseModel):
    """Response with action steps for C# to execute."""
    session_id: str
    steps: List[ActionStep]
    schema_version: str = "1.0.0"


# Simple intent-to-action mappings for common commands
INTENT_PATTERNS = {
    "open notepad": [
        ActionStep(action="open_app", target="notepad.exe")
    ],
    "open chrome": [
        ActionStep(action="open_app", target="chrome.exe")
    ],
    "open browser": [
        ActionStep(action="open_app", target="chrome.exe")
    ],
    "open calculator": [
        ActionStep(action="open_app", target="calc.exe")
    ],
    "open explorer": [
        ActionStep(action="open_app", target="explorer.exe")
    ],
    "open word": [
        ActionStep(action="open_app", target="winword.exe")
    ],
    "open excel": [
        ActionStep(action="open_app", target="excel.exe")
    ],
}


def parse_command(command: str) -> List[ActionStep]:
    """
    Parse user command into action steps.
    
    Supports:
    - "open [app]" - Opens an application
    - "type [text]" - Types text  
    - "search [query]" - Searches for something
    - "go to [url]" - Navigates to URL
    """
    command_lower = command.lower().strip()
    
    # Check exact matches first
    if command_lower in INTENT_PATTERNS:
        return INTENT_PATTERNS[command_lower]
    
    # Parse "open X" commands
    if command_lower.startswith("open "):
        app_name = command[5:].strip()
        # Map common names to executables
        app_mapping = {
            "notepad": "notepad.exe",
            "chrome": "chrome.exe",
            "browser": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "explorer": "explorer.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "vscode": "code.exe",
            "code": "code.exe",
            "terminal": "wt.exe",
            "cmd": "cmd.exe",
            "paint": "mspaint.exe",
        }
        exe = app_mapping.get(app_name.lower(), f"{app_name}.exe")
        return [ActionStep(action="open_app", target=exe)]
    
    # Parse "type X" commands
    if command_lower.startswith("type "):
        text = command[5:].strip()
        return [ActionStep(action="type_text", content=text)]
    
    # Parse "search X" or "search for X" commands
    if command_lower.startswith("search for "):
        query = command[11:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    if command_lower.startswith("search "):
        query = command[7:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    
    # Parse "go to X" or "navigate to X" commands
    if command_lower.startswith("go to "):
        url = command[6:].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=url)
        ]
    if command_lower.startswith("navigate to "):
        url = command[12:].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=url)
        ]
    
    # Parse "click X" commands (placeholder - needs coordinates)
    if command_lower.startswith("click "):
        target = command[6:].strip()
        return [ActionStep(action="click", target=target)]
    
    # Default: try to open as app
    return [ActionStep(action="open_app", target=f"{command_lower}.exe")]


@router.post("/plan", response_model=PlanResponse)
async def get_action_plan(request: PlanRequest):
    """
    Get action plan for a user command.
    
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
        steps = parse_command(request.command)
        
        return PlanResponse(
            session_id=session_id,
            steps=steps,
            schema_version="1.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health():
    """Health check for agent API."""
    return {"status": "ready", "version": "1.0.0"}
