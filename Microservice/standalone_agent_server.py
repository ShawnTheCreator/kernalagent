"""
Minimal standalone server for Desktop Agent integration.
Run this directly to test the /api/agent/plan endpoint.

Usage:
    cd kernalagent-contrib/Microservice
    .\venv\Scripts\activate
    python standalone_agent_server.py
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import uvicorn
import json
import asyncio
from datetime import datetime

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

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()


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


# Authentication endpoints for C# client
@app.post("/api/auth/sync")
async def auth_sync(request: Request = None):
    """Authentication sync endpoint for C# client."""
    if request:
        try:
            body = await request.json()
            device_id = body.get("deviceId", "demo_device")
            token = body.get("token", "demo_token")
            
            return {
                "success": True,
                "method": "websocket",
                "deviceId": device_id,
                "token": token
            }
        except:
            pass
    
    return {
        "status": "success",
        "authenticated": True,
        "user_id": "demo_user",
        "session_id": str(uuid.uuid4()),
        "message": "Authentication successful"
    }


@app.get("/api/auth/status")
async def auth_status():
    """Authentication status endpoint."""
    return {
        "authenticated": True,
        "user_id": "demo_user",
        "session_active": True
    }


@app.get("/api/auth/poll")
async def poll_auth(deviceId: str = "demo_device"):
    """Fast local polling for desktop login."""
    return {
        "token": "demo_token_" + str(uuid.uuid4())[:8],
        "status": "success"
    }


@app.post("/api/vision/find-target")
async def find_click_target(request: Request):
    """Vision analysis endpoint for finding click targets."""
    try:
        body = await request.json()
        screenshot = body.get("screenshot", "")
        target = body.get("target", "button")
        
        # Mock vision response
        return {
            "success": True,
            "x": 100,
            "y": 200,
            "element": target,
            "confidence": 0.95,
            "message": f"Found {target} at coordinates (100, 200)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Vision analysis failed"
        }


@app.get("/api/agent/health")
async def agent_health_check():
    """Agent health check endpoint."""
    return {
        "status": "ready",
        "version": "1.0.0",
        "model": "gemini-2.5-flash",
        "capabilities": ["chat", "commands", "vision", "speech"]
    }


@app.post("/api/speech/transcribe")
async def transcribe_speech(request: Request):
    """Speech transcription endpoint."""
    try:
        body = await request.json()
        audio_data = body.get("audio_data", "")
        
        # Mock transcription
        return {
            "transcript": "open notepad",
            "confidence": 0.95,
            "language": "en-US"
        }
    except Exception as e:
        return {
            "error": str(e),
            "transcript": "",
            "confidence": 0.0
        }


@app.get("/api/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": [
            {
                "id": "janitor",
                "name": "Janitor Agent",
                "description": "File organization and cleanup",
                "status": "active"
            },
            {
                "id": "assistant",
                "name": "Assistant Agent", 
                "description": "General purpose assistant",
                "status": "active"
            }
        ]
    }


@app.get("/api/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get specific agent status."""
    return {
        "agent_id": agent_id,
        "status": "active",
        "last_activity": datetime.now().isoformat(),
        "capabilities": ["file_operations", "organization"]
    }


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with C# client."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Parse JSON message
            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")
                
                if message_type == "ping":
                    # Send pong response
                    await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
                elif message_type == "command":
                    # Handle command message
                    command = message.get("command", "")
                    session_id = message.get("session_id", str(uuid.uuid4()))
                    
                    # Parse command and get steps
                    steps = parse_command(command)
                    
                    # Send response
                    response = {
                        "type": "plan_response",
                        "session_id": session_id,
                        "steps": [
                            {
                                "action": step.action,
                                "target": step.target,
                                "url": step.url,
                                "query": step.query,
                                "content": step.content
                            }
                            for step in steps
                        ],
                        "schema_version": "1.0.0"
                    }
                    await manager.send_personal_message(json.dumps(response), websocket)
                else:
                    # Echo unknown messages
                    await manager.send_personal_message(json.dumps({
                        "type": "echo",
                        "original": message
                    }), websocket)
                    
            except json.JSONDecodeError:
                # Send error for invalid JSON
                await manager.send_personal_message(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    print("=" * 60)
    print("🧠 Kernal Agent - Enhanced Desktop Integration Server")
    print("=" * 60)
    print()
    print("Endpoints:")
    print("  POST /api/agent/plan      - Get action plan for command")
    print("  POST /api/auth/sync       - Authentication sync")
    print("  GET  /api/auth/status     - Authentication status")
    print("  GET  /api/auth/poll       - Authentication polling")
    print("  POST /api/vision/find-target - Vision analysis")
    print("  GET  /api/agent/health    - Agent health check")
    print("  POST /api/speech/transcribe - Speech transcription")
    print("  GET  /api/agents          - List available agents")
    print("  GET  /api/agents/{id}     - Get agent status")
    print("  GET  /health              - Health check")
    print("  WS   /ws/stream           - WebSocket communication")
    print()
    print("Starting on http://0.0.0.0:8001")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
