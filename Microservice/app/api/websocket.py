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
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

from app.engine.vision import analyze_frame
from app.db.skills_repo import increment_skill_usage, get_skill_by_id
from app.agent.memory import AgentMemory
from app.api.ws_manager import manager
from app.vision.frame_differ import FrameDiffer
from app.core.smart_rate_limiter import get_rate_limiter
from app.core.model_router import get_model_router, TaskType, TaskComplexity

logger = logging.getLogger(__name__)
router = APIRouter()

# Global state
CURRENT_INTENT: str = "Waiting for command..."
PREVIOUS_ACTION: Optional[dict] = None
PREVIOUS_FRAME: Optional[str] = None
AGENT_MEMORY: AgentMemory = AgentMemory()

# Gemini 3 Upgrade Components
FRAME_DIFFER: FrameDiffer = FrameDiffer(stability_threshold=0.95)
RATE_LIMITER = get_rate_limiter()
MODEL_ROUTER = get_model_router()


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
                            # Use ORIGINAL user message for planning, not just intent
                            planning_command = user_message  # Original message like "open chrome"
                            print(f"[BRAIN] → ACT (confident): {planning_command}")
                            
                            # Store for "do that again"
                            ctx = get_context(session_id)
                            ctx.last_intent = brain_output.intent
                            ctx.last_target = brain_output.target
                            
                            # === NEW: Call LLM planner and send actions to C# ===
                            try:
                                from app.reasoning.llm_planner import plan_command_with_fallback
                                
                                # Get action steps from LLM planner using ORIGINAL message
                                steps = await plan_command_with_fallback(planning_command, session_id)
                                
                                if steps:
                                    print(f"[BRAIN] Got {len(steps)} action steps from planner")
                                    
                                    # Send action plan to C# executor
                                    await websocket.send_json({
                                        "type": "action_plan",
                                        "payload": {
                                            "steps": steps,
                                            "original_command": planning_command,
                                            "brain_reply": brain_output.message,  # LLM's friendly response
                                            "confidence": brain_output.confidence
                                        }
                                    })
                                    
                                    # Broadcast to frontends
                                    await manager.broadcast_to_frontends({
                                        "type": "agent_state",
                                        "state": "EXECUTING",
                                        "title": "Executing Action",
                                        "description": f"Running: {planning_command}"
                                    })
                                else:
                                    print(f"[BRAIN] Planner returned no steps")
                                    await websocket.send_json({
                                        "type": "chat_response",
                                        "payload": {
                                            "message": f"I understood '{planning_command}' but couldn't figure out how to do it. Can you try rephrasing?",
                                            "reasoning": "Planner returned empty"
                                        }
                                    })
                            except Exception as e:
                                print(f"[BRAIN] Planner error: {e}")
                                import traceback
                                traceback.print_exc()
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "payload": {
                                        "message": f"I ran into an issue trying to execute that. Error: {str(e)[:100]}",
                                        "reasoning": f"Planner error: {e}"
                                    }
                                })
                            
                            continue
                            
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
                
                # Only reach here on fallback
                PREVIOUS_ACTION = None
                PREVIOUS_FRAME = None
                AGENT_MEMORY.reset()
                print(f"[INTENT] Fallback proceeding with: {CURRENT_INTENT}")
                
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
                    
                current_frame = data.get("image")
                
                # === FRAME DIFFER: Skip stable frames to reduce API calls ===
                is_significant, similarity = FRAME_DIFFER.is_significant_change(current_frame)
                
                if not is_significant:
                    logger.info(f"[VISION] Frame stable (similarity: {similarity:.3f}), skipping API call")
                    # Send no-change response to C#
                    await websocket.send_json({
                        "type": "action",
                        "payload": {
                            "action_type": "WAIT",
                            "reason": "UI unchanged",
                            "confidence": 1.0
                        }
                    })
                    await asyncio.sleep(1.0)  # Short wait before next frame
                    continue
                
                logger.info(f"[VISION] Significant UI change detected (similarity: {similarity:.3f})")
                logger.info(f"[VISION] Analyzing Frame for: {CURRENT_INTENT}")
                
                # Broadcast analyzing state to frontends
                await manager.broadcast_to_frontends({
                    "type": "agent_state",
                    "state": "OBSERVING",
                    "title": "Analyzing Screen",
                    "description": f"Vision processing for: {CURRENT_INTENT}"
                })
                
                # === RATE LIMITER: Prevent 429 errors ===
                user_id = session_id or "anonymous"
                if not await RATE_LIMITER.acquire(user_id, tier="free"):
                    logger.warning(f"[RATE_LIMIT] User {user_id} rate limited")
                    await websocket.send_json({
                        "type": "error",
                        "payload": {
                            "message": "Rate limit exceeded. Please wait a moment.",
                            "retry_after": 5
                        }
                    })
                    await asyncio.sleep(5.0)
                    continue
                
                # === VISION PROCESSING with rate limit tracking ===
                try:
                    action_plan = await asyncio.to_thread(
                        analyze_frame,
                        current_frame,
                        CURRENT_INTENT,
                        PREVIOUS_ACTION,
                        PREVIOUS_FRAME,
                        AGENT_MEMORY
                    )
                    
                    # Report success to rate limiter
                    RATE_LIMITER.report_success()
                    
                except Exception as e:
                    # Check if it's a 429 error
                    if "429" in str(e) or "rate" in str(e).lower():
                        RATE_LIMITER.report_429()
                        logger.error(f"[RATE_LIMIT] 429 error from Gemini API")
                        await websocket.send_json({
                            "type": "error",
                            "payload": {
                                "message": "API rate limit hit. Backing off.",
                                "retry_after": 10
                            }
                        })
                        await asyncio.sleep(10.0)
                        continue
                    else:
                        logger.error(f"[VISION] Error: {e}")
                        raise

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
            
            # Handle window state changes from C# (minimize/restore)
            if msg_type == "window_state":
                state = data.get("state", "")
                print(f"[WS] Window state changed: {state}")
                
                try:
                    from app.gui.floating_widget import get_widget_manager, init_floating_widget
                    widget_manager = get_widget_manager()
                    
                    if state == "minimized":
                        # Lazily start the widget if not already running
                        if not widget_manager._running:
                            print("[WS] Starting floating widget for the first time...")
                            init_floating_widget()
                        
                        print("[WS] Showing floating widget")
                        widget_manager.show()
                    elif state == "restored":
                        print("[WS] Hiding floating widget")
                        widget_manager.hide()
                except ImportError:
                    print("[WS] Floating widget not available (PyQt5 not installed)")
                except Exception as e:
                    print(f"[WS] Error handling window state: {e}")
                    import traceback
                    traceback.print_exc()
    
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
