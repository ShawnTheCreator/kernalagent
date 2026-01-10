"""
WebSocket API for Kernal Agent AI Brain.
Handles real-time communication with the Desktop Client.
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.engine.vision import analyze_frame

router = APIRouter()

# Global state for current user intent
CURRENT_INTENT = "Waiting for command..."


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for the Kernal nervous system.
    
    Protocol:
    - Client sends {"type": "intent_update", "payload": "user's goal"}
    - Client sends {"type": "frame", "image": "base64 encoded screenshot"}
    - Server responds with {"type": "action", "payload": {...action plan...}}
    """
    global CURRENT_INTENT
    await websocket.accept()
    print("[CONNECTED] Nervous System Connected (C# Client Online)")

    try:
        while True:
            data = await websocket.receive_json()

            # Handle intent updates
            if data.get("type") == "intent_update":
                CURRENT_INTENT = data.get("payload")
                print(f"[INTENT] New Intent: {CURRENT_INTENT}")
                continue

            # Handle frame analysis requests
            if data.get("type") == "frame":
                if CURRENT_INTENT == "Waiting for command...":
                    continue 
                print(f"[VISION] Analyzing Frame for: {CURRENT_INTENT}")

                # Run vision analysis in thread pool to avoid blocking
                action_plan = await asyncio.to_thread(
                    analyze_frame,
                    data.get("image"),
                    CURRENT_INTENT
                )

                response = {
                    "type": "action",
                    "payload": action_plan
                }
                await websocket.send_json(response)

                # Throttle to respect rate limits
                await asyncio.sleep(4.0)
    
    except WebSocketDisconnect:
        print("[DISCONNECTED] Nervous System Severed")
    except Exception as e:
        print(f"[ERROR] Critical Error: {e}")
