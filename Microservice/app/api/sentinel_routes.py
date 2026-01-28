"""
Sentinel WebSocket endpoint for real-time alerts.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

from app.api.sentinel_ws import get_ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()
ws_manager = get_ws_manager()


@router.websocket("/ws/sentinel")
async def sentinel_websocket(
    websocket: WebSocket,
    user_id: str = Query(default="anonymous")
):
    """
    WebSocket endpoint for Sentinel real-time alerts.
    
    Connect with: ws://localhost:8000/ws/sentinel?user_id=your_user_id
    
    Messages received:
    - sentinel_alert: System alerts (CPU, memory, temperature, disk, processes)
    - sentinel_health_score: Overall system health score (0-100)
    - sentinel_status: Initial status and user profile
    
    Messages sent:
    - sentinel_action: User response to alerts
    - update_profile: Update user preferences
    - whitelist_process: Whitelist a process from alerts
    """
    await ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle the message
            await ws_manager.handle_message(websocket, user_id, data)
            
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"[Sentinel WS] Error for user {user_id}: {e}")
        await ws_manager.disconnect(user_id)
