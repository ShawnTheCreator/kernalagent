"""
Kernal Agent AI Brain - FastAPI Application Entry Point.

This is the main server that powers the Kernal Agent desktop copilot.
It provides a WebSocket API for real-time communication with the Desktop Client.
"""
import logging
import sys
import time

# ===== CENTRALIZED LOGGING SETUP =====
# Configure logging FIRST before any imports
# This ensures all modules use the same logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Force stdout for immediate flush
    ],
    force=True  # Override any existing config
)

# Make sure output is not buffered
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Set uvicorn loggers to INFO as well
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.websocket import router as websocket_router
from app.api.skills import router as skills_router
from app.api.agent_routes import router as agent_router
from app.api.protected_routes import router as protected_router  # Authenticated user APIs
from app.api.agent_plan import router as agent_plan_router  # Desktop Agent HTTP API
from app.api.executor_ws import router as executor_ws_router  # Hybrid WebSocket executor
from app.api.speech_routes import router as speech_router  # Voice transcription API
from app.api.voice_ws import router as voice_ws_router  # Continuous voice WebSocket
from app.api.agent_hub_routes import router as agent_hub_router  # Agent Hub API
from app.core.config import settings
from app.db.init_db import init_database


# ===== REQUEST/RESPONSE LOGGING MIDDLEWARE =====
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log incoming request
        start_time = time.time()
        body = b""
        
        # Try to get request body for POST requests
        if request.method == "POST":
            try:
                body = await request.body()
                # Log the body (truncate if too long)
                body_str = body.decode('utf-8')[:500] if body else ""
                logger.info(f"📥 REQUEST: {request.method} {request.url.path}")
                logger.info(f"📥 BODY: {body_str}")
            except Exception as e:
                logger.warning(f"Could not read request body: {e}")
        else:
            logger.info(f"📥 REQUEST: {request.method} {request.url.path}")
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(f"📤 RESPONSE: {response.status_code} ({process_time:.0f}ms)")
            
            return response
        except Exception as e:
            logger.error(f"❌ REQUEST FAILED: {e}")
            raise


# Initialize database on startup
init_database()

# Create FastAPI application
app = FastAPI(
    title="Kernal Agent AI Brain",
    description="The cognitive engine for the Kernal Agent desktop copilot",
    version="0.1.0"
)

# Add request logging middleware FIRST
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(websocket_router)
app.include_router(skills_router)
app.include_router(agent_router)  # Agent preview APIs for frontend
app.include_router(protected_router)  # Protected user APIs (/me/*)
app.include_router(agent_plan_router)  # Desktop Agent HTTP API (/api/agent/plan)
app.include_router(executor_ws_router)  # Hybrid WebSocket executor (/ws/executor)
app.include_router(speech_router)  # Voice transcription API (/api/speech/*)
app.include_router(voice_ws_router)  # Continuous voice WebSocket (/ws/voice)
app.include_router(agent_hub_router)  # Agent Hub API (/api/agents/*)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "alive", "model": settings.MODEL_ID}


# ===== LOCAL AUTH SYNC (REAL-TIME WEBSOCKET) =====
# Instant desktop login via WebSocket broadcast

from app.api.ws_manager import manager as ws_manager

_pending_logins = {}  # deviceId -> token (fallback for polling)


@app.post("/api/auth/sync")
async def sync_auth_token(request: Request):
    """
    Called by web frontend after user logs in.
    Broadcasts token via WebSocket to C# app for INSTANT auth (no polling delay).
    """
    try:
        body = await request.json()
        device_id = body.get("deviceId")
        token = body.get("token")
        
        if not device_id or not token:
            return {"success": False, "error": "Missing deviceId or token"}
        
        # Store for polling fallback
        _pending_logins[device_id] = token
        
        # INSTANT: Broadcast to C# client via WebSocket
        auth_message = {
            "type": "auth_success",
            "deviceId": device_id,
            "token": token
        }
        await ws_manager.send_to_csharp(auth_message)
        
        logger.info(f"[AUTH-SYNC] Token broadcasted via WebSocket for device: {device_id[:8]}...")
        return {"success": True, "method": "websocket"}
    except Exception as e:
        logger.error(f"[AUTH-SYNC] Error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/auth/poll")
async def poll_auth_local(deviceId: str):
    """
    Fast local polling for desktop login.
    Returns token if web login completed, 404 if still pending.
    """
    if deviceId in _pending_logins:
        token = _pending_logins.pop(deviceId)  # One-time use
        logger.info(f"[AUTH-POLL] Token retrieved for device: {deviceId[:8]}...")
        return {"token": token}
    
    return {"error": "Login pending", "status": "waiting"}


@app.post("/api/vision/find-target")
async def find_click_target(request: Request):
    """
    Find a clickable target using vision analysis.
    
    Called by C# SmartExecutor when a step has requires_vision_targeting=True.
    This enables commands like "click on any video" to find actual coordinates.
    
    Request body:
        screenshot: base64 encoded screenshot
        target: description of what to find (e.g., "any video", "first result")
        goal: optional context about user's overall goal
    
    Returns:
        success: bool
        x: pixel x coordinate (center of element)
        y: pixel y coordinate (center of element)
        element: description of what was found
        confidence: 0.0-1.0
    """
    from app.vision.vision_targeting import find_click_target
    
    try:
        body = await request.json()
        screenshot = body.get("screenshot")
        target = body.get("target", "element")
        goal = body.get("goal", "")
        
        if not screenshot:
            return {"success": False, "error": "No screenshot provided"}
        
        result = await find_click_target(screenshot, target, goal)
        
        if result and result.get("found") and result.get("x") and result.get("y"):
            logger.info(f"[VISION-TARGET] Found '{target}' at ({result['x']}, {result['y']})")
            return {
                "success": True,
                "x": result["x"],
                "y": result["y"],
                "element": result.get("element", "unknown"),
                "confidence": result.get("confidence", 0.5)
            }
        
        logger.warning(f"[VISION-TARGET] Could not find: {target}")
        return {
            "success": False, 
            "error": f"Target not found: {target}",
            "reason": result.get("reason") if result else "Vision analysis failed"
        }
        
    except Exception as e:
        logger.error(f"[VISION-TARGET] Error: {e}")
        return {"success": False, "error": str(e)}


@app.on_event("startup")
async def startup_event():
    # Register agents on startup
    from app.agents.agent_registry import get_registry
    from app.agents.janitor.janitor_agent import JanitorAgent
    
    registry = get_registry()
    if registry.get("JANITOR_AGENT") is None:
        registry.register(JanitorAgent())
    
    # Start Janitor Daemon (autonomous mode)
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        from app.api.ws_manager import manager as ws_manager
        
        daemon = get_janitor_daemon()
        
        # Set up WebSocket notifications for file events
        async def on_permission_needed(action):
            """Send permission request to frontend via WebSocket."""
            await ws_manager.broadcast({
                "type": "janitor_permission",
                "action_id": action["id"],
                "file": action["file_info"].get("filename"),
                "suggestion": action["result"].suggestion,
                "capability": action["result"].capability,
            })
        
        async def on_action_completed(result, success):
            """Notify frontend when action completes."""
            await ws_manager.broadcast({
                "type": "janitor_action",
                "capability": result.capability,
                "action": result.action_type,
                "success": success,
                "message": result.suggestion,
            })
        
        daemon.on_permission_needed = on_permission_needed
        daemon.on_action_completed = on_action_completed
        
        await daemon.start()
        logger.info("🧹 Janitor Daemon started in autonomous mode")
    except Exception as e:
        logger.warning(f"Janitor Daemon not started: {e}")
    
    logger.info("=" * 60)
    logger.info("🚀 KERNAL AGENT BRAIN STARTING UP")
    logger.info("=" * 60)
    logger.info(f"📡 Available endpoints:")
    logger.info(f"   POST /api/agent/plan        - v1 planning (Gemini)")
    logger.info(f"   POST /api/agent/plan/v2     - v2 LLM-first planning")
    logger.info(f"   POST /api/vision/find-target - vision targeting")
    logger.info(f"   POST /api/auth/sync         - fast auth sync (local)")
    logger.info(f"   GET  /api/auth/poll         - fast auth poll (local)")
    logger.info(f"   GET  /api/agents            - list agents (NEW)")
    logger.info(f"   GET  /api/agents/janitor/quick-scan - janitor scan (NEW)")
    logger.info(f"   GET  /health                - health check")
    logger.info("=" * 60)
    logger.info("🧹 Janitor watching Downloads & Desktop for new files")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Kernal Agent Brain...")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")

