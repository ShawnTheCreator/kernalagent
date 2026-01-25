"""
WebSocket endpoint for real-time continuous voice recognition.

Provides:
- /ws/voice - WebSocket for continuous voice streaming
- Start/stop/status control messages
- Real-time transcription updates
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from app.speech.continuous_voice import (
    get_continuous_recognizer, 
    VoiceConfig, 
    VoiceState,
    ContinuousVoiceRecognizer
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections
active_connections: dict[str, WebSocket] = {}


class VoiceWebSocketHandler:
    """Handler for a single WebSocket voice session."""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.recognizer: Optional[ContinuousVoiceRecognizer] = None
    
    async def send_message(self, msg_type: str, data: dict = None):
        """Send JSON message to WebSocket client."""
        message = {"type": msg_type, **(data or {})}
        await self.websocket.send_json(message)
    
    def setup_callbacks(self):
        """Set up recognizer callbacks that send to WebSocket."""
        if not self.recognizer:
            return
        
        loop = asyncio.get_event_loop()
        
        def on_transcription(text: str, is_final: bool):
            asyncio.run_coroutine_threadsafe(
                self.send_message("transcription", {
                    "text": text, 
                    "is_final": is_final
                }),
                loop
            )
        
        def on_command(text: str):
            asyncio.run_coroutine_threadsafe(
                self.send_message("command", {"text": text}),
                loop
            )
        
        def on_wake_word():
            asyncio.run_coroutine_threadsafe(
                self.send_message("wake_word", {}),
                loop
            )
        
        def on_stop_word():
            asyncio.run_coroutine_threadsafe(
                self.send_message("stop_word", {}),
                loop
            )
        
        def on_state_change(state: VoiceState):
            asyncio.run_coroutine_threadsafe(
                self.send_message("state", {"state": state.value}),
                loop
            )
        
        def on_error(error: str):
            asyncio.run_coroutine_threadsafe(
                self.send_message("error", {"error": error}),
                loop
            )
        
        self.recognizer.on_transcription = on_transcription
        self.recognizer.on_command = on_command
        self.recognizer.on_wake_word = on_wake_word
        self.recognizer.on_stop_word = on_stop_word
        self.recognizer.on_state_change = on_state_change
        self.recognizer.on_error = on_error
    
    async def handle_message(self, message: dict):
        """Handle incoming WebSocket message."""
        msg_type = message.get("type", "")
        
        if msg_type == "start":
            # Start continuous listening
            config_data = message.get("config", {})
            config = VoiceConfig(
                always_listening=config_data.get("always_listening", True),
                silence_timeout_sec=config_data.get("silence_timeout", 1.5),
                wake_words=config_data.get("wake_words"),
                stop_words=config_data.get("stop_words"),
            )
            
            self.recognizer = get_continuous_recognizer(config)
            self.setup_callbacks()
            
            success = self.recognizer.start()
            await self.send_message("started" if success else "error", {
                "success": success,
                "state": self.recognizer.get_state().value if success else "error"
            })
        
        elif msg_type == "stop":
            # Stop listening
            if self.recognizer:
                self.recognizer.stop()
                await self.send_message("stopped", {})
        
        elif msg_type == "status":
            # Get current status
            if self.recognizer:
                await self.send_message("status", {
                    "listening": self.recognizer.is_listening(),
                    "state": self.recognizer.get_state().value
                })
            else:
                await self.send_message("status", {
                    "listening": False,
                    "state": "not_initialized"
                })
        
        elif msg_type == "ping":
            await self.send_message("pong", {})
        
        else:
            await self.send_message("error", {"error": f"Unknown message type: {msg_type}"})
    
    def cleanup(self):
        """Clean up resources."""
        if self.recognizer and self.recognizer.is_listening():
            self.recognizer.stop()


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for continuous voice recognition."""
    await websocket.accept()
    
    session_id = str(id(websocket))
    handler = VoiceWebSocketHandler(websocket, session_id)
    active_connections[session_id] = websocket
    
    logger.info(f"[VOICE-WS] Client connected: {session_id}")
    
    try:
        # Send welcome message
        await handler.send_message("connected", {
            "session_id": session_id,
            "message": "Voice WebSocket connected. Send 'start' to begin listening."
        })
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handler.handle_message(message)
            except json.JSONDecodeError:
                await handler.send_message("error", {"error": "Invalid JSON"})
    
    except WebSocketDisconnect:
        logger.info(f"[VOICE-WS] Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"[VOICE-WS] Error: {e}")
    finally:
        handler.cleanup()
        active_connections.pop(session_id, None)


# HTTP endpoints for non-WebSocket control

@router.post("/voice/start")
async def start_voice():
    """Start continuous voice recognition (HTTP fallback)."""
    recognizer = get_continuous_recognizer()
    success = recognizer.start()
    return {
        "success": success,
        "state": recognizer.get_state().value,
        "message": "Use WebSocket at /ws/voice for real-time updates"
    }


@router.post("/voice/stop")
async def stop_voice():
    """Stop continuous voice recognition."""
    recognizer = get_continuous_recognizer()
    recognizer.stop()
    return {"success": True, "state": recognizer.get_state().value}


@router.get("/voice/status")
async def voice_status():
    """Get voice recognition status."""
    recognizer = get_continuous_recognizer()
    return {
        "listening": recognizer.is_listening(),
        "state": recognizer.get_state().value
    }
