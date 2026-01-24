"""
WebSocket API for Kernal Agent AI Brain.
Handles real-time communication with the Desktop Client and Frontend Dashboard.

Features:
- C# executor connection for receiving frames and sending commands
- Frontend connection for broadcasting real-time action events
- Skill execution command handling
- Action history and memory management
"""
import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from app.engine.vision import analyze_frame
from app.db.skills_repo import increment_skill_usage, get_skill_by_id
from app.agent.memory import AgentMemory
from app.api.ws_manager import manager

router = APIRouter()

# Global state
CURRENT_INTENT: str = "Waiting for command..."
PREVIOUS_ACTION: Optional[dict] = None
PREVIOUS_FRAME: Optional[str] = None
AGENT_MEMORY: AgentMemory = AgentMemory()


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None, client_type: str = "frontend"):
    """
    Main WebSocket endpoint for the Kernal nervous system.
    
    Query params:
    - client_type: "csharp" for C# executor, "frontend" for dashboards
    
    Protocol:
    - C# sends {"type": "intent_update", "payload": "user's goal"}
    - C# sends {"type": "frame", "image": "base64 encoded screenshot"}
    - C# sends {"type": "action_executed", "payload": {...executed action...}}
    - Server sends {"type": "action", "payload": {...action plan...}}
    - Server sends {"type": "run_skill", "payload": {...skill details...}}
    
    Frontend receives:
    - {"type": "action_executed", ...} for activity timeline
    - {"type": "agent_state", ...} for status updates
    """
    global CURRENT_INTENT, PREVIOUS_ACTION, PREVIOUS_FRAME
    
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    # Determine client type from first message or query param
    await manager.connect(websocket, client_type)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            # Client identifying itself
            if msg_type == "identify":
                identified_type = data.get("client_type", "frontend")
                manager.connection_types[websocket] = identified_type
                print(f"[WS] Client identified as: {identified_type}")
                continue
            
            # Handle intent updates (from C# or voice command)
            if msg_type == "intent_update":
                user_message = data.get("payload", "")
                print(f"[INTENT] Received: {user_message}")
                
                # ===== NEW: Route through Conversational Brain first =====
                try:
                    from app.brain import process_message, BrainOutputType
                    from app.brain.conversation_context import get_context
                    
                    brain_output = await process_message(user_message, session_id)
                    print(f"[BRAIN] Output: type={brain_output.type}, confidence={brain_output.confidence}")
                    
                    # --- CHAT: Pure conversation, no automation ---
                    if brain_output.type == BrainOutputType.CHAT:
                        print(f"[BRAIN] → CHAT response")
                        
                        # Send response back to C# client
                        await websocket.send_json({
                            "type": "chat_response",
                            "payload": {
                                "message": brain_output.message,
                                "reasoning": brain_output.reasoning
                            }
                        })
                        
                        # Broadcast to frontends
                        await manager.broadcast_to_frontends({
                            "type": "agent_state",
                            "state": "CHATTING",
                            "title": "Conversation",
                            "description": brain_output.message[:100] if brain_output.message else ""
                        })
                        continue
                    
                    # --- ASK: Need clarification ---
                    if brain_output.type == BrainOutputType.ASK:
                        print(f"[BRAIN] → ASK: {brain_output.question}")
                        
                        # Send question back to C# client
                        await websocket.send_json({
                            "type": "ask_question",
                            "payload": {
                                "question": brain_output.question,
                                "about": brain_output.intent,
                                "reasoning": brain_output.reasoning
                            }
                        })
                        
                        # Broadcast to frontends
                        await manager.broadcast_to_frontends({
                            "type": "agent_state",
                            "state": "WAITING",
                            "title": "Waiting for Clarification",
                            "description": brain_output.question[:100] if brain_output.question else ""
                        })
                        continue
                    
                    # --- ACT: Execute automation (confidence >= 0.7) ---
                    if brain_output.type == BrainOutputType.ACT:
                        if brain_output.confidence >= 0.7:
                            # High confidence → proceed with execution
                            CURRENT_INTENT = f"{brain_output.intent} {brain_output.target or ''}".strip()
                            print(f"[BRAIN] → ACT (confident): {CURRENT_INTENT}")
                            
                            # Store for "do that again"
                            ctx = get_context(session_id)
                            ctx.last_intent = brain_output.intent
                            ctx.last_target = brain_output.target
                            
                        else:
                            # Low confidence → ask for confirmation
                            print(f"[BRAIN] → ACT (low confidence: {brain_output.confidence:.0%})")
                            await websocket.send_json({
                                "type": "ask_question",
                                "payload": {
                                    "question": f"I'm {brain_output.confidence:.0%} sure you want to {brain_output.intent} {brain_output.target or ''}. Should I proceed?",
                                    "about": "confirmation",
                                    "reasoning": brain_output.reasoning
                                }
                            })
                            continue
                            
                except ImportError as e:
                    print(f"[BRAIN] Import error, falling back to direct: {e}")
                    CURRENT_INTENT = user_message
                except Exception as e:
                    print(f"[BRAIN] Error, falling back to direct: {e}")
                    import traceback
                    traceback.print_exc()
                    CURRENT_INTENT = user_message
                
                # Reset state for new intent
                PREVIOUS_ACTION = None
                PREVIOUS_FRAME = None
                AGENT_MEMORY.reset()
                print(f"[INTENT] Proceeding with: {CURRENT_INTENT}")
                
                # Broadcast intent to frontends
                await manager.broadcast_to_frontends({
                    "type": "agent_state",
                    "state": "PLANNING",
                    "title": "Processing Intent",
                    "description": CURRENT_INTENT
                })
                continue

            # Handle frame analysis requests (from C#)
            if msg_type == "frame":
                if CURRENT_INTENT == "Waiting for command...":
                    continue 
                    
                print(f"[VISION] Analyzing Frame for: {CURRENT_INTENT}")
                
                # Broadcast analyzing state to frontends
                await manager.broadcast_to_frontends({
                    "type": "agent_state",
                    "state": "OBSERVING",
                    "title": "Analyzing Screen",
                    "description": f"Vision processing for: {CURRENT_INTENT}"
                })

                current_frame = data.get("image")

                action_plan = await asyncio.to_thread(
                    analyze_frame,
                    current_frame,
                    CURRENT_INTENT,
                    PREVIOUS_ACTION,
                    PREVIOUS_FRAME,
                    AGENT_MEMORY
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

                # Send action to C# executor
                response = {
                    "type": "action",
                    "payload": action_plan
                }
                await websocket.send_json(response)
                
                # Broadcast action to frontends for activity timeline
                await manager.broadcast_to_frontends({
                    "type": "action_executed",
                    "state": "EXECUTING",
                    "title": action_plan.get("action_type", "ACTION"),
                    "description": action_plan.get("reason", ""),
                    "action": action_plan
                })
                
                # Store state for next frame
                PREVIOUS_ACTION = action_plan
                PREVIOUS_FRAME = current_frame

                # Check if task is complete
                if action_plan.get("action_type") == "DONE":
                    print(f"[COMPLETE] Task completed: {CURRENT_INTENT}")
                    
                    await manager.broadcast_to_frontends({
                        "type": "agent_state",
                        "state": "IDLE",
                        "title": "Task Complete",
                        "description": f"Completed: {CURRENT_INTENT}"
                    })
                    
                    CURRENT_INTENT = "Waiting for command..."
                    PREVIOUS_ACTION = None
                    PREVIOUS_FRAME = None
                    AGENT_MEMORY.reset()

                # Adaptive throttling based on confidence
                confidence = action_plan.get("confidence", 0.5)
                if confidence >= 0.8:
                    wait_time = 2.0
                elif confidence >= 0.5:
                    wait_time = 4.0
                else:
                    wait_time = 6.0
                    
                await asyncio.sleep(wait_time)
            
            # Handle action execution reports from C# (for real-time display)
            if msg_type == "action_executed":
                payload = data.get("payload", {})
                print(f"[C# ACTION] Executed: {payload.get('action', 'unknown')}")
                
                # Broadcast to all frontends
                await manager.broadcast_to_frontends({
                    "type": "action_executed",
                    "state": "EXECUTING",
                    "title": payload.get("action", "Action"),
                    "description": payload.get("target", payload.get("content", "")),
                    "action": payload
                })
            
            # Handle skill execution command (from frontend "Play" button)
            if msg_type == "run_skill":
                skill_id = data.get("skill_id")
                print(f"[WS] Received run_skill command for: {skill_id}")
                
                # Forward to C# executor
                sent = await manager.send_to_csharp({
                    "type": "run_skill",
                    "skill_id": skill_id
                })
                
                if sent:
                    await manager.broadcast_to_frontends({
                        "type": "agent_state",
                        "state": "EXECUTING",
                        "title": "Running Skill",
                        "description": f"Executing skill: {skill_id}"
                    })
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        print("[DISCONNECTED] Client disconnected")
        PREVIOUS_ACTION = None
        PREVIOUS_FRAME = None
        AGENT_MEMORY.reset()
    except Exception as e:
        await manager.disconnect(websocket)
        print(f"[ERROR] WebSocket Error: {e}")
        import traceback
        traceback.print_exc()


async def broadcast_skill_execution(skill_id: str, skill_name: str):
    """
    Called by the skills API to trigger skill execution via WebSocket.
    """
    print(f"[SKILLS] Broadcasting skill execution: {skill_name}")
    
    # Send run command to C# executor
    sent = await manager.send_to_csharp({
        "type": "run_skill",
        "skill_id": skill_id,
        "skill_name": skill_name
    })
    
    # Notify frontends
    await manager.broadcast_to_frontends({
        "type": "agent_state",
        "state": "EXECUTING",
        "title": f"Running: {skill_name}",
        "description": f"Executing skill from dashboard"
    })
    
    return sent
