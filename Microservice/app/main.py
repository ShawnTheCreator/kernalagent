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


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "alive", "model": settings.MODEL_ID}


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 KERNAL AGENT BRAIN STARTING UP")
    logger.info("=" * 60)
    logger.info(f"📡 Available endpoints:")
    logger.info(f"   POST /api/agent/plan     - v1 planning (Gemini)")
    logger.info(f"   POST /api/agent/plan/v2  - v2 LLM-first planning")
    logger.info(f"   GET  /health             - health check")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Kernal Agent Brain...")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")

