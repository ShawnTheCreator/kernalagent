"""
WebSocket API for Kernal Agent AI Brain.
Handles real-time communication with the Desktop Client.

Now includes:
- Previous action state tracking for failure detection
- Previous frame tracking for vision signal detection
- Skill usage tracking
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from app.engine.vision import analyze_frame
from app.db.skills_repo import increment_skill_usage
from app.agent.memory import AgentMemory

router = APIRouter()

# Global state
CURRENT_INTENT: str = "Waiting for command..."
PREVIOUS_ACTION: Optional[dict] = None
PREVIOUS_FRAME: Optional[str] = None
AGENT_MEMORY: AgentMemory = AgentMemory()  # Session-scoped STM


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for the Kernal nervous system.
    
    Protocol:
    - Client sends {"type": "intent_update", "payload": "user's goal"}
    - Client sends {"type": "frame", "image": "base64 encoded screenshot"}
    - Server responds with {"type": "action", "payload": {...action plan...}}
    
    Enhanced with:
    - Action history for failure detection
    - Skill reuse tracking
    - Confidence-based throttling
    """
    global CURRENT_INTENT, PREVIOUS_ACTION, PREVIOUS_FRAME
    
    await websocket.accept()
    print("[CONNECTED] Nervous System Connected (C# Client Online)")

    try:
        while True:
            data = await websocket.receive_json()

            # Handle intent updates
            if data.get("type") == "intent_update":
                CURRENT_INTENT = data.get("payload")
                PREVIOUS_ACTION = None  # Reset action history on new intent
                PREVIOUS_FRAME = None
                AGENT_MEMORY.reset()  # Reset STM on new intent
                print(f"[INTENT] New Intent: {CURRENT_INTENT}")
                print(f"[STM] Memory reset for new intent")
                continue

            # Handle frame analysis requests
            if data.get("type") == "frame":
                if CURRENT_INTENT == "Waiting for command...":
                    continue 
                    
                print(f"[VISION] Analyzing Frame for: {CURRENT_INTENT}")

                # Get current frame
                current_frame = data.get("image")

                # Run vision analysis in thread pool to avoid blocking
                action_plan = await asyncio.to_thread(
                    analyze_frame,
                    current_frame,
                    CURRENT_INTENT,
                    PREVIOUS_ACTION,
                    PREVIOUS_FRAME,
                    AGENT_MEMORY  # Pass STM to vision engine
                )

                # Track skill usage if skill was used
                if action_plan.get("skill_id") and action_plan.get("strategy") == "REUSE_SKILL":
                    try:
                        await asyncio.to_thread(
                            increment_skill_usage,
                            action_plan.get("skill_id")
                        )
                        print(f"[SKILL] Incremented usage for: {action_plan.get('skill_id')}")
                    except Exception as e:
                        print(f"[SKILL] Failed to increment usage: {e}")

                # Build response
                response = {
                    "type": "action",
                    "payload": action_plan
                }
                
                await websocket.send_json(response)
                
                # Store state for next frame
                PREVIOUS_ACTION = action_plan
                PREVIOUS_FRAME = current_frame

                # Check if task is complete
                if action_plan.get("action_type") == "DONE":
                    print(f"[COMPLETE] Task completed: {CURRENT_INTENT}")
                    CURRENT_INTENT = "Waiting for command..."
                    PREVIOUS_ACTION = None
                    PREVIOUS_FRAME = None
                    AGENT_MEMORY.reset()  # Reset STM on task completion
                    print(f"[STM] Memory reset after task completion")

                # Adaptive throttling based on confidence
                confidence = action_plan.get("confidence", 0.5)
                if confidence >= 0.8:
                    wait_time = 2.0  # Fast for high confidence
                elif confidence >= 0.5:
                    wait_time = 4.0  # Normal
                else:
                    wait_time = 6.0  # Slower for low confidence
                    
                await asyncio.sleep(wait_time)
    
    except WebSocketDisconnect:
        print("[DISCONNECTED] Nervous System Severed")
        PREVIOUS_ACTION = None
        PREVIOUS_FRAME = None
        AGENT_MEMORY.reset()  # Reset STM on disconnect
        print(f"[STM] Memory reset after disconnect")
    except Exception as e:
        print(f"[ERROR] Critical Error: {e}")
        import traceback
        traceback.print_exc()
