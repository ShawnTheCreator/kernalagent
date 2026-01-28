"""
Sentinel WebSocket Routes - Real-time alerts and notifications.

Provides WebSocket endpoints for Sentinel daemon communication.
"""

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends

from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon

logger = logging.getLogger(__name__)


async def get_current_user(websocket: WebSocket) -> str:
    """Extract user ID from WebSocket query params."""
    # For now, use query param. Later integrate with auth
    user_id = websocket.query_params.get("user_id", "anonymous")
    return user_id


class SentinelWebSocketManager:
    """Manages WebSocket connections for Sentinel alerts."""
    
    def __init__(self):
        self.daemon = get_sentinel_daemon()
        self.connections: Dict[str, WebSocket] = {}  # user_id -> websocket
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and register with daemon."""
        await websocket.accept()
        
        # Store connection
        self.connections[user_id] = websocket
        
        # Register with daemon
        await self.daemon.register_client(websocket, user_id)
        
        # Send initial status
        await self.send_status(websocket, user_id)
        
        logger.info(f"[Sentinel WS] User connected: {user_id}")
    
    async def disconnect(self, user_id: str):
        """Handle WebSocket disconnection."""
        if user_id in self.connections:
            websocket = self.connections[user_id]
            await self.daemon.unregister_client(websocket)
            del self.connections[user_id]
        
        logger.info(f"[Sentinel WS] User disconnected: {user_id}")
    
    async def send_status(self, websocket: WebSocket, user_id: str):
        """Send initial status to connected client."""
        status = {
            "type": "sentinel_status",
            "daemon_status": self.daemon.get_status(),
            "user_profile": self.daemon.user_profiles.get(user_id, {}),
            "timestamp": "now"
        }
        
        try:
            await websocket.send_text(json.dumps(status))
        except Exception as e:
            logger.error(f"[Sentinel WS] Failed to send status: {e}")
    
    async def handle_message(self, websocket: WebSocket, user_id: str, message: Dict):
        """Handle incoming message from client."""
        message_type = message.get("type")
        
        if message_type == "sentinel_action":
            # User responded to an alert
            await self.daemon.handle_user_response({
                **message,
                "user_id": user_id
            })
        
        elif message_type == "update_profile":
            # Update user preferences
            self.daemon.user_profiles[user_id].update(message.get("profile", {}))
            
        elif message_type == "whitelist_process":
            # Whitelist a process
            process_name = message.get("process_name")
            await self.daemon._whitelist_process(process_name)
        
        else:
            logger.warning(f"[Sentinel WS] Unknown message type: {message_type}")


# Global manager
_ws_manager = None

def get_ws_manager() -> SentinelWebSocketManager:
    """Get the WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = SentinelWebSocketManager()
    return _ws_manager
