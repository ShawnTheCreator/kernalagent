"""
Kernal Agent AI Brain - FastAPI Application Entry Point.

This is the main server that powers the Kernal Agent desktop copilot.
It provides a WebSocket API for real-time communication with the Desktop Client.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.websocket import router as websocket_router
from app.api.skills import router as skills_router
from app.core.config import settings
from app.db.init_db import init_database

# Initialize database on startup
init_database()

# Create FastAPI application
app = FastAPI(
    title="Kernal Agent AI Brain",
    description="The cognitive engine for the Kernal Agent desktop copilot",
    version="0.1.0"
)

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


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "alive", "model": settings.MODEL_ID}


if __name__ == "__main__":
    import uvicorn
    print("Starting Kernal Agent Brain...")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
