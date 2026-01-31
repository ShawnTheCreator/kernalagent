"""
Hybrid WebSocket Executor Endpoint.

This provides real-time bidirectional communication for:
- Command execution with progress feedback
- Frame/screenshot analysis
- Status updates

Protocol:
    C# → Python:
        {"type": "connect", "session_id": "..."}
        {"type": "command", "payload": "open notepad"}
        {"type": "frame", "image": "base64..."}
        {"type": "result", "command_id": "...", "status": "SUCCESS"}
    
    Python → C#:
        {"type": "connected", "session_id": "..."}
        {"type": "action", "payload": {...}}
        {"type": "status", "message": "..."}
        {"type": "done", "success": true}
"""
import asyncio
import uuid
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional, Any

from app.executor import CommandGenerator, Target, Command, ActionType
from app.core.smart_rate_limiter import get_rate_limiter
from app.core.model_router import get_model_router, TaskType, TaskComplexity
from app.reasoning.thinking_planner import get_thinking_planner

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Active sessions
SESSIONS: Dict[str, dict] = {}

# Gemini 3 Upgrade Components
RATE_LIMITER = get_rate_limiter()
MODEL_ROUTER = get_model_router()
THINKING_PLANNER = get_thinking_planner()


async def parse_command_llm(command: str, session_id: str, user_id: str = "anonymous") -> list:
    """
    Parse command using LLM-first planner with model router and rate limiting.
    Routes to thinking planner for complex tasks, fast planner for simple tasks.
    """
    logger.info(f"[WS/EXECUTOR] Parsing command with LLM: '{command}'")
    
    # === RATE LIMITER: Check if we can make API call ===
    if not await RATE_LIMITER.acquire(user_id, tier="free"):
        logger.warning(f"[WS/EXECUTOR] Rate limited for user {user_id}")
        return [{
            "action": "error",
            "message": "Rate limit exceeded. Please wait a moment.",
            "retry_after": 5
        }]
    
    try:
        # === MODEL ROUTER: Determine task complexity ===
        # Estimate complexity from command text
        complexity = MODEL_ROUTER._estimate_complexity(command)
        logger.info(f"[WS/EXECUTOR] Task complexity: {complexity.name}")
        
        # === THINKING PLANNER for complex tasks ===
        if complexity == TaskComplexity.COMPLEX:
            logger.info(f"[WS/EXECUTOR] Using THINKING PLANNER for complex task")
            
            plan = await THINKING_PLANNER.plan_complex_workflow(
                intent=command,
                context={
                    "session_id": session_id,
                    "user_id": user_id
                }
            )
            
            if plan and "steps" in plan:
                RATE_LIMITER.report_success()
                logger.info(f"[WS/EXECUTOR] Thinking planner returned {len(plan['steps'])} steps")
                return plan["steps"]
        
        # === STANDARD PLANNER for simple/medium tasks ===
        else:
            logger.info(f"[WS/EXECUTOR] Using STANDARD planner for {complexity.name} task")
            from app.reasoning.llm_planner import plan_command_with_fallback
            
            steps = await plan_command_with_fallback(command, session_id)
            RATE_LIMITER.report_success()
            
            logger.info(f"[WS/EXECUTOR] Standard planner returned {len(steps)} steps")
            return steps
        
    except Exception as e:
        # Check for 429 rate limit errors
        if "429" in str(e) or "rate" in str(e).lower():
            RATE_LIMITER.report_429()
            logger.error(f"[WS/EXECUTOR] 429 error from Gemini API")
            return [{
                "action": "error",
                "message": "API rate limit hit. Backing off.",
                "retry_after": 10
            }]
        
        logger.error(f"[WS/EXECUTOR] LLM planner failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to simple parsing if LLM completely fails
        return parse_command_simple(command)


def parse_command_simple(command: str) -> list:
    """Simple fallback parser (old logic)."""
    logger.warning(f"[WS/EXECUTOR] Using SIMPLE parser (fallback) for: {command}")
    cmd = command.lower().strip()
    
    APP_MAPPING = {
        "notepad": "notepad.exe", "chrome": "chrome.exe", "browser": "chrome.exe",
        "firefox": "firefox.exe", "edge": "msedge.exe", "calculator": "calc.exe",
        "calc": "calc.exe", "explorer": "explorer.exe", "word": "winword.exe",
        "excel": "excel.exe", "vscode": "code.exe", "code": "code.exe",
        "terminal": "wt.exe", "cmd": "cmd.exe", "paint": "mspaint.exe",
    }
    
    if cmd.startswith("open "):
        app = command[5:].strip().lower()
        exe = APP_MAPPING.get(app, f"{app}.exe")
        return [{"action": "open_app", "target": exe}]
    
    if cmd.startswith("type "):
        return [{"action": "type_text", "content": command[5:].strip()}]
    
    if cmd.startswith("search for "):
        query = command[11:].strip()
        return [
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": f"https://www.google.com/search?q={query}"}
        ]
    
    if cmd.startswith("search "):
        query = command[7:].strip()
        return [
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": f"https://www.google.com/search?q={query}"}
        ]
    
    if cmd.startswith("go to ") or cmd.startswith("navigate to "):
        url = command.split(" to ", 1)[1].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        return [
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": url}
        ]
    
    return [{"action": "open_app", "target": f"{cmd}.exe"}]


@router.websocket("/ws/executor")
async def executor_websocket(websocket: WebSocket):
    """
    Hybrid WebSocket endpoint for real-time command execution.
    
    Features:
    - Simple commands via "command" message type
    - Frame analysis via "frame" message type  
    - Result reporting from C# executor
    - Progress status updates to C#
    """
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "connected_at": datetime.utcnow().isoformat(),
        "last_command": None,
        "pending_commands": [],
        "completed_count": 0
    }
    
    logger.info(f"[WS/EXECUTOR] ✅ Connected: {session_id}")
    
    # Send connected confirmation
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            # === CONNECT ===
            if msg_type == "connect":
                client_session = data.get("session_id")
                if client_session:
                    # Resume existing session
                    if client_session in SESSIONS:
                        session_id = client_session
                        logger.info(f"[WS/EXECUTOR] Resumed session: {session_id}")
                
                await websocket.send_json({
                    "type": "connected",
                    "session_id": session_id,
                    "resumed": client_session == session_id
                })
            
            # === COMMAND ===
            elif msg_type == "command":
                command_text = data.get("payload", "")
                command_id = data.get("command_id", str(uuid.uuid4())[:8])
                user_id = data.get("user_id", session_id)  # Use session_id as fallback user_id
                
                logger.info(f"[WS/EXECUTOR] ========================================")
                logger.info(f"[WS/EXECUTOR] 📥 COMMAND RECEIVED: '{command_text}'")
                logger.info(f"[WS/EXECUTOR] Command ID: {command_id}")
                logger.info(f"[WS/EXECUTOR] User ID: {user_id}")
                logger.info(f"[WS/EXECUTOR] ========================================")
                
                # Send status update
                await websocket.send_json({
                    "type": "status",
                    "message": f"Processing: {command_text}",
                    "command_id": command_id
                })
                
                # Parse command into steps using LLM planner with rate limiting and model routing
                steps = await parse_command_llm(command_text, session_id, user_id)
                
                # Track in session
                SESSIONS[session_id]["last_command"] = command_text
                SESSIONS[session_id]["pending_commands"].append(command_id)
                
                # Send action plan
                await websocket.send_json({
                    "type": "action",
                    "command_id": command_id,
                    "payload": {
                        "session_id": session_id,
                        "steps": steps,
                        "total_steps": len(steps),
                        "schema_version": "1.0.0"
                    }
                })
                
                logger.info(f"[WS/EXECUTOR] 📤 SENT {len(steps)} steps for command '{command_text}'")
            
            # === RESULT (from C# executor) ===
            elif msg_type == "result":
                command_id = data.get("command_id")
                status = data.get("status", "UNKNOWN")
                step_index = data.get("step_index", 0)
                error = data.get("error")
                
                logger.info(f"[WS/EXECUTOR] 📊 Result: cmd={command_id}, step={step_index}, status={status}")
                
                if command_id in SESSIONS[session_id]["pending_commands"]:
                    if status == "SUCCESS":
                        SESSIONS[session_id]["completed_count"] += 1
                    elif status == "FAILED":
                        # Remove from pending
                        SESSIONS[session_id]["pending_commands"].remove(command_id)
                        await websocket.send_json({
                            "type": "error",
                            "command_id": command_id,
                            "message": error or "Execution failed"
                        })
                    elif status == "DONE":
                        # Command fully completed
                        SESSIONS[session_id]["pending_commands"].remove(command_id)
                        await websocket.send_json({
                            "type": "done",
                            "command_id": command_id,
                            "success": True
                        })
            
            # === STEP_PROGRESS (real-time step updates from C#) ===
            elif msg_type == "step_progress":
                command_id = data.get("command_id")
                step_index = data.get("step_index", 0)
                total_steps = data.get("total_steps", 0)
                action = data.get("action", "")
                status = data.get("status", "running")  # running, success, failed
                details = data.get("details", "")
                
                logger.info(f"[WS/EXECUTOR] 📈 Progress: step {step_index + 1}/{total_steps} - {action} ({status})")
                
                # Broadcast progress (could be sent to UI WebSocket)
                # For now, just log it - UI can subscribe to this
                SESSIONS[session_id]["current_step"] = {
                    "index": step_index,
                    "total": total_steps,
                    "action": action,
                    "status": status,
                    "details": details
                }
                
                # Echo back confirmation
                await websocket.send_json({
                    "type": "progress_ack",
                    "command_id": command_id,
                    "step_index": step_index,
                    "received": True
                })
            
            # === FRAME (screenshot for vision analysis) ===
            elif msg_type == "frame":
                # Placeholder for vision integration
                # In full implementation, this would call analyze_frame()
                image_data = data.get("image", "")
                
                await websocket.send_json({
                    "type": "status",
                    "message": "Frame received (vision analysis pending)"
                })
                
                # TODO: Integrate with app.engine.vision.analyze_frame()
                logger.info(f"[WS/EXECUTOR] 🖼️ Frame received ({len(image_data)} chars)")
            
            # === PING (keepalive) ===
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            # === UNKNOWN ===
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"[WS/EXECUTOR] ❌ Disconnected: {session_id}")
        # Keep session data for potential reconnect
    except Exception as e:
        logger.error(f"[WS/EXECUTOR] 💥 Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Cleanup old sessions after some time
        pass


@router.get("/ws/executor/sessions")
async def list_sessions():
    """Debug endpoint to list active sessions."""
    return {
        "active_sessions": len(SESSIONS),
        "sessions": {
            sid: {
                "connected_at": data["connected_at"],
                "last_command": data["last_command"],
                "completed_count": data["completed_count"]
            }
            for sid, data in SESSIONS.items()
        }
    }
