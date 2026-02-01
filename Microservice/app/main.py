"""
Kernel AI Brain - FastAPI Application Entry Point.

This is the main server that powers the Kernel desktop copilot.
It provides a WebSocket API for real-time communication with the Desktop Client.
"""
import logging
import sys
import time
import os

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
from app.api.agent_plan import kernel_router as kernel_router  # Kernel strict endpoints
from app.api.executor_ws import router as executor_ws_router  # Hybrid WebSocket executor
from app.api.speech_routes import router as speech_router  # Voice transcription API
from app.api.voice_ws import router as voice_ws_router  # Continuous voice WebSocket
from app.api.agent_hub_routes import router as agent_hub_router  # Agent Hub API
from app.api.tts_routes import router as tts_router  # TTS API (/api/tts/*)
from app.api.memory_api import router as memory_router  # Memory and patterns API
from app.api.gemma_routes import router as gemma_router  # Fine-tuned Gemma API
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

# ===== GEMINI 3 UPGRADE: INITIALIZE COMPONENTS =====
@app.on_event("startup")
async def startup_event():
    """Initialize Gemini 3 upgrade components on startup."""
    logger.info("🚀 Initializing Gemini 3 Upgrade Components...")
    
    try:
        # Initialize model router
        from app.core.model_router import get_model_router
        router = get_model_router()
        logger.info(f"✅ Model Router initialized: {router.models}")
        
        # Initialize thinking planner
        from app.reasoning.thinking_planner import get_thinking_planner
        planner = get_thinking_planner()
        logger.info(f"✅ Thinking Planner initialized with model: {planner.model_id}")
        
        # Initialize rate limiter
        from app.core.smart_rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        logger.info(f"✅ Rate Limiter initialized")
        
        # Initialize frame differ
        from app.vision.frame_differ import FrameDiffer
        differ = FrameDiffer()
        logger.info(f"✅ Frame Differ initialized (threshold: {differ.stability_threshold})")
        
        # Initialize fine-tuned Gemma model
        try:
            from app.brain.gemma_local import is_model_available, load_model
            if is_model_available():
                logger.info("🧠 Fine-tuned Gemma model found, loading...")
                model, tokenizer = load_model()
                if model is not None:
                    logger.info("✅ Fine-tuned Gemma interpreter loaded!")
                else:
                    logger.warning("⚠️ Gemma model found but failed to load")
            else:
                logger.info("ℹ️ Fine-tuned Gemma model not found (optional)")
        except Exception as e:
            logger.warning(f"⚠️ Gemma model initialization skipped: {e}")
        
        logger.info("🎉 Gemini 3 Upgrade Components Ready!")
        logger.info(f"   - Model Router: ✅")
        logger.info(f"   - Thinking Planner: ✅")
        logger.info(f"   - Rate Limiter: ✅")
        logger.info(f"   - Frame Differ: ✅")
        logger.info(f"   - Vision: {'✅ ENABLED' if settings.ENABLE_VISION else '❌ DISABLED'}")
        logger.info(f"   - Structured Outputs: {'✅ ENABLED' if settings.ENABLE_STRUCTURED_OUTPUT else '❌ DISABLED'}")
        logger.info(f"   - Floating Widget: ✅ (lazy-loaded when minimized)")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini 3 components: {e}")
        import traceback
        traceback.print_exc()

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
app.include_router(kernel_router)  # Kernel strict endpoints (/api/kernel/*)
app.include_router(executor_ws_router)  # Hybrid WebSocket executor (/ws/executor)
app.include_router(speech_router)  # Voice transcription API (/api/speech/*)
app.include_router(voice_ws_router)  # Continuous voice WebSocket (/ws/voice)
app.include_router(agent_hub_router)  # Agent Hub API (/api/agents/*)
app.include_router(tts_router)  # TTS API (/api/tts/*)
app.include_router(memory_router)  # Memory and patterns API (/api/memory/*)
app.include_router(gemma_router)  # Fine-tuned Gemma API (/api/gemma/*)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "alive", "model": settings.MODEL_ID}


# ===== GEMINI 3 MONITORING ENDPOINTS =====
@app.get("/api/gemini3/stats")
async def get_gemini3_stats():
    """Get statistics for all Gemini 3 upgrade components."""
    try:
        from app.core.model_router import get_model_router
        from app.core.smart_rate_limiter import get_rate_limiter
        from app.vision.frame_differ import FrameDiffer
        from app.api.websocket import FRAME_DIFFER
        
        router = get_model_router()
        limiter = get_rate_limiter()
        
        # Get model router stats
        router_stats = router.get_stats()
        
        # Get rate limiter stats
        limiter_stats = limiter.get_stats()
        
        # Get frame differ stats
        frame_stats = FRAME_DIFFER.get_stats()
        
        return {
            "success": True,
            "timestamp": time.time(),
            "components": {
                "model_router": {
                    "enabled": True,
                    "models": router.models,
                    "stats": router_stats
                },
                "rate_limiter": {
                    "enabled": True,
                    "stats": limiter_stats
                },
                "frame_differ": {
                    "enabled": True,
                    "threshold": FRAME_DIFFER.stability_threshold,
                    "stats": frame_stats
                },
                "features": {
                    "vision": settings.ENABLE_VISION,
                    "structured_output": settings.ENABLE_STRUCTURED_OUTPUT,
                    "thinking_mode": settings.ENABLE_THINKING_MODE
                }
            }
        }
    except Exception as e:
        logger.error(f"[GEMINI3] Stats error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/gemini3/model-decisions")
async def get_model_decisions():
    """Get recent model routing decisions for analysis."""
    try:
        from app.core.model_router import get_model_router
        router = get_model_router()
        stats = router.get_stats()
        
        return {
            "success": True,
            "decisions": stats.get("decisions_by_type", {}),
            "total_decisions": stats.get("total_decisions", 0),
            "models_used": stats.get("models_used", {})
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/gemini3/reset-stats")
async def reset_gemini3_stats():
    """Reset statistics for monitoring (useful for testing)."""
    try:
        from app.core.model_router import get_model_router
        from app.core.smart_rate_limiter import get_rate_limiter
        from app.api.websocket import FRAME_DIFFER
        
        # Reset all stats
        get_model_router()._reset_stats()
        FRAME_DIFFER.reset()
        
        return {"success": True, "message": "All Gemini 3 stats reset"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    # Auto: rebuild semantic memory embeddings on startup
    try:
        from app.db.memory_bridge import rebuild_memory_embeddings
        from app.db.episodic_memory_repo import list_local_session_ids

        rebuild_force = os.getenv("MEMORY_REBUILD_FORCE", "false").lower() == "true"
        rebuild_limit = int(os.getenv("MEMORY_REBUILD_LIMIT", "500"))
        rebuild_session_id = os.getenv("MEMORY_REBUILD_SESSION_ID", "").strip()

        session_ids = list_local_session_ids()
        if rebuild_session_id:
            session_ids.append(rebuild_session_id)

        for session_id in session_ids:
            if not session_id:
                continue
            result = await rebuild_memory_embeddings(
                user_id=session_id,
                limit=rebuild_limit,
                force=rebuild_force
            )
            logger.info(
                f"[MEMORY] Startup embedding rebuild for {session_id}: {result}"
            )
    except Exception as e:
        logger.warning(f"[MEMORY] Startup embedding rebuild skipped: {e}")

    # Register all enhanced agents
    try:
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        from app.voice.enhanced_voice_control import get_voice_control
        from app.notifications.notification_manager import get_notification_manager

        logger.info("🤖 Registering enhanced agents...")
        
        registry = get_registry()
        
        # Register all new agents
        registry.register(JanitorAgent())
        registry.register(ProductivityAgent())
        registry.register(SecurityAgent())
        
        # Start enhanced systems
        voice_control = get_voice_control()
        await voice_control.start_voice_control()
        
        notification_manager = get_notification_manager()
        
        logger.info(f"✅ Registered {len(registry.get_all())} agents")
        logger.info("✅ Enhanced voice control started")
        logger.info("✅ Notification system initialized")
        
        # Log registered agents
        for agent in registry.get_all():
            logger.info(f"   - {agent.name} ({agent.agent_type.value})")
            
    except Exception as e:
        logger.error(f"❌ Agent registration failed: {e}")

    logger.info("=" * 60)
    logger.info("🚀 KERNEL AI BRAIN STARTING UP")
    logger.info("=" * 60)
    logger.info(f"📡 Available endpoints:")
    logger.info(f"   POST /api/agent/plan        - v1 planning (Gemini)")
    logger.info(f"   POST /api/agent/plan/v2     - v2 LLM-first planning")
    logger.info(f"   POST /api/vision/find-target - vision targeting")
    logger.info(f"   POST /api/auth/sync         - fast auth sync (local)")
    logger.info(f"   GET  /api/auth/poll         - fast auth poll (local)")
    logger.info(f"   GET  /api/agents            - list agents (NEW)")
    logger.info(f"   GET  /health                - health check")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Kernel AI Brain...")
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        log_level="info", 
        reload=True,
        ws_ping_timeout=60,
        ws_ping_interval=20
    )

