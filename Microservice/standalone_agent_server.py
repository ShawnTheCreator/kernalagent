"""
Minimal standalone server for Desktop Agent integration.
Run this directly to test the /api/agent/plan endpoint.

Usage:
    cd kernalagent-contrib/Microservice
    .\venv\Scripts\activate
    python standalone_agent_server.py
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import uvicorn

# ==================== Models ====================

class PlanRequest(BaseModel):
    command: str
    session_id: Optional[str] = None


class ActionStep(BaseModel):
    action: str
    target: Optional[str] = None
    url: Optional[str] = None
    query: Optional[str] = None
    content: Optional[str] = None


class PlanResponse(BaseModel):
    session_id: str
    steps: List[ActionStep]
    schema_version: str = "1.0.0"


# ==================== Command Parser ====================

APP_MAPPING = {
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


def parse_command(command: str) -> List[ActionStep]:
    """Parse user command into action steps."""
    cmd = command.lower().strip()
    
    # "open X"
    if cmd.startswith("open "):
        app = command[5:].strip().lower()
        exe = APP_MAPPING.get(app, f"{app}.exe")
        return [ActionStep(action="open_app", target=exe)]
    
    # "type X"
    if cmd.startswith("type "):
        text = command[5:].strip()
        return [ActionStep(action="type_text", content=text)]
    
    # "search for X" or "search X"
    if cmd.startswith("search for "):
        query = command[11:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    if cmd.startswith("search "):
        query = command[7:].strip()
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=f"https://www.google.com/search?q={query}")
        ]
    
    # "go to X" or "navigate to X"
    if cmd.startswith("go to ") or cmd.startswith("navigate to "):
        url = command.split(" to ", 1)[1].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return [
            ActionStep(action="open_app", target="chrome.exe"),
            ActionStep(action="navigate", url=url)
        ]
    
    # Default: try as app
    return [ActionStep(action="open_app", target=f"{cmd}.exe")]


# ==================== FastAPI App ====================

app = FastAPI(
    title="Kernal Agent - Desktop Integration Server",
    description="HTTP API for C# Desktop Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ready", "version": "1.0.0"}


@app.get("/api/agent/health")
async def agent_health():
    return {"status": "ready", "version": "1.0.0"}


@app.post("/api/agent/plan", response_model=PlanResponse)
async def get_action_plan(request: PlanRequest):
    """
    Get action plan for a user command.
    
    Called by C# Desktop Agent's VoiceToActionService.
    
    Examples:
        {"command": "open notepad"}
        {"command": "type hello world"}
        {"command": "search for weather"}
        {"command": "go to google.com"}
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        steps = parse_command(request.command)
        print(f"[AGENT] Command: '{request.command}' -> {len(steps)} steps")
        for i, step in enumerate(steps):
            print(f"        Step {i+1}: {step.action} -> {step.target or step.content or step.url}")
        
        return PlanResponse(
            session_id=session_id,
            steps=steps,
            schema_version="1.0.0"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("=" * 60)
    print("🧠 Kernal Agent - Desktop Integration Server")
    print("=" * 60)
    print()
    print("Endpoints:")
    print("  POST /api/agent/plan  - Get action plan for command")
    print("  GET  /health          - Health check")
    print()
    print("Starting on http://0.0.0.0:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
