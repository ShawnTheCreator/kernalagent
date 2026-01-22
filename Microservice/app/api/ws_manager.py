"""
WebSocket Connection Manager for Kernal Agent.

Tracks connected clients (C# desktop app, frontend dashboards) and enables
bidirectional broadcasting of events.
"""
from typing import List, Dict, Optional, Any
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    
    Supports:
    - Multiple connected clients (C# executor, multiple frontend dashboards)
    - Broadcasting events to all clients
    - Sending targeted messages to specific client types
    """
    
    def __init__(self):
        # All active connections
        self.active_connections: List[WebSocket] = []
        # Map connection to client type ("csharp", "frontend")
        self.connection_types: Dict[WebSocket, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_type: str = "frontend"):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            self.connection_types[websocket] = client_type
        print(f"[WS MANAGER] New {client_type} client connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                client_type = self.connection_types.pop(websocket, "unknown")
                print(f"[WS MANAGER] {client_type} client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to ALL connected clients."""
        if not self.active_connections:
            return
        
        json_message = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                print(f"[WS MANAGER] Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def broadcast_to_frontends(self, message: Dict[str, Any]):
        """Broadcast a message only to frontend clients."""
        json_message = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            if self.connection_types.get(connection) == "frontend":
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    print(f"[WS MANAGER] Failed to send to frontend: {e}")
                    disconnected.append(connection)
        
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_to_csharp(self, message: Dict[str, Any]):
        """Send a message to the C# desktop client."""
        json_message = json.dumps(message)
        disconnected = []
        sent = False
        
        for connection in self.active_connections:
            if self.connection_types.get(connection) == "csharp":
                try:
                    await connection.send_text(json_message)
                    sent = True
                    print(f"[WS MANAGER] Sent command to C# executor: {message.get('type')}")
                except Exception as e:
                    print(f"[WS MANAGER] Failed to send to C# client: {e}")
                    disconnected.append(connection)
        
        for conn in disconnected:
            await self.disconnect(conn)
        
        return sent
    
    def get_csharp_connection(self) -> Optional[WebSocket]:
        """Get the C# client connection if connected."""
        for connection in self.active_connections:
            if self.connection_types.get(connection) == "csharp":
                return connection
        return None
    
    @property
    def csharp_connected(self) -> bool:
        """Check if C# client is connected."""
        return any(t == "csharp" for t in self.connection_types.values())
    
    @property
    def frontend_count(self) -> int:
        """Count of connected frontend clients."""
        return sum(1 for t in self.connection_types.values() if t == "frontend")


# Global singleton instance
manager = ConnectionManager()
