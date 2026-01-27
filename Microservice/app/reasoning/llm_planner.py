"""
LLM-First Planner - Unified Planning Pipeline

Replaces if-else logic with:
    Intent Analyzer → Tool Registry → Context Memory → Executor Steps

This is the main entry point for the new architecture.
"""

import os
import re
import logging
import sys
from typing import List, Dict, Any, Optional

# Setup logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Feature flag for gradual rollout
USE_LLM_FIRST = os.getenv("USE_LLM_FIRST", "true").lower() == "true"


def preprocess_command(command: str) -> str:
    """
    Preprocess command to help LLM parse correctly.
    Converts 'type X and Y' → 'type X. Then Y'
    """
    if " and " not in command.lower():
        return command
    
    original = command
    
    # Pattern: "type X and [verb]" → "type X. Then [verb]"
    command = re.sub(
        r'\btype\s+([^a]+?)\s+and\s+(press|click|save|open)',
        r'type \1. Then \2',
        command,
        flags=re.IGNORECASE
    )
    
    if command != original:
        logger.info(f"[PREPROCESSOR] '{original}' → '{command}'")
    
    return command


async def plan_command(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Main planning function - LLM-first with intelligent fallbacks.
    
    Pipeline:
    0. Preprocess command (fix 'type X and Y')
    1. Check for contextual commands ("do that again")
    1.5. Check for agent match (NEW - Janitor, etc.)
    2. Check plan cache (skip LLM if cached)
    3. Analyze intent with LLM (Gemini → Groq)
    4. Convert to executor steps
    5. Cache successful plan
    6. Update context
    
    Args:
        command: User's natural language command
        session_id: Session ID for context
    
    Returns:
        List of executor-ready action dicts
    """
    from app.reasoning.intent_analyzer import analyze_command
    from app.executor.tools import convert_plan_to_executor_steps
    from app.memory.context import (
        get_context_for_llm,
        is_contextual_command,
        resolve_contextual_command,
        update_session,
    )
    from app.core.plan_cache import get_plan_cache
    
    logger.info(f"[PLANNER] ========== PROCESSING COMMAND ==========")
    logger.info(f"[PLANNER] Command: '{command}'")
    logger.info(f"[PLANNER] Session: {session_id}")
    
    # ===== Step 0: Preprocess Command =====
    command = preprocess_command(command)
    
    # ===== Step 1: Check Contextual Commands =====
    if is_contextual_command(command):
        resolved = resolve_contextual_command(command, session_id)
        if resolved:
            logger.info(f"[PLANNER] Resolved contextual command: {resolved}")
            # Update context and return
            update_session(session_id, command, resolved)
            return [resolved]
    
    # ===== Step 1.5: Check for Agent Match (NEW) =====
    try:
        from app.agents.agent_planner import should_route_to_agent, get_agent_for_intent
        
        agent_name = await should_route_to_agent(command)
        if agent_name:
            logger.info(f"[PLANNER] 🤖 Agent matched: {agent_name}")
            agent = await get_agent_for_intent(command)
            
            if agent:
                logger.info(f"[PLANNER] Delegating to {agent.name}...")
                
                # Run agent's analyze -> plan lifecycle
                context = {"intent": command, "session_id": session_id}
                analysis = await agent.analyze(context)
                plan = await agent.plan(analysis)

                # Always return a single meta-step when an agent matches.
                # IMPORTANT: even if the agent produces 0 executable actions, the agent may
                # still have produced useful findings (e.g., a health report). We must not
                # fall through into UI automation planning.
                summary = None
                try:
                    findings = getattr(analysis, "findings", {}) or {}
                    health_report = findings.get("health_report", {})
                    
                    # Generate detailed, intent-specific summary
                    if isinstance(health_report, dict):
                        # Extract detailed metrics
                        cpu_info = health_report.get("cpu", {})
                        memory_info = health_report.get("memory", {})
                        temp_info = health_report.get("temperature", {})
                        disk_info = health_report.get("disk", {})
                        network_info = health_report.get("network", {})
                        
                        # Build detailed summary based on intent
                        intent_lower = command.lower()
                        
                        if "metrics" in intent_lower or "real-time" in intent_lower:
                            # Real-time metrics format
                            cpu_pct = cpu_info.get("percent_total", 0)
                            mem_pct = ((memory_info.get("virtual", {})).get("percent_used", 0))
                            temp = temp_info.get("max_temp", "N/A")
                            disk_usage = ((disk_info.get("c", {})).get("percent_used", 0)) if disk_info.get("c") else 0
                            
                            summary = (
                                f"📊 Real-time System Metrics:\n"
                                f"• CPU: {cpu_pct}% (cores: {cpu_info.get('cores', 'N/A')})\n"
                                f"• RAM: {mem_pct}% (used: {memory_info.get('virtual', {}).get('used_gb', 'N/A')}GB / {memory_info.get('virtual', {}).get('total_gb', 'N/A')}GB)\n"
                                f"• Temperature: {temp}°C\n"
                                f"• Disk C: {disk_usage}% used\n"
                                f"• Network: ↑{network_info.get('bytes_sent_per_sec', 0):.1f}KB/s ↓{network_info.get('bytes_recv_per_sec', 0):.1f}KB/s"
                            )
                        elif "temperature" in intent_lower or "thermal" in intent_lower:
                            # Temperature-focused summary
                            temps = temp_info.get("sensors", {})
                            temp_list = [f"{name}: {t['temp']}°C" for name, t in temps.items()]
                            summary = (
                                f"🌡️ Thermal Status:\n"
                                f"• Max Temperature: {temp_info.get('max_temp', 'N/A')}°C\n"
                                f"• Sensors: {', '.join(temp_list) if temp_list else 'N/A'}\n"
                                f"• Fan Status: {temp_info.get('fan_status', 'N/A')}"
                            )
                        elif "cpu" in intent_lower:
                            # CPU-focused summary
                            summary = (
                                f"⚡ CPU Performance:\n"
                                f"• Total Usage: {cpu_info.get('percent_total', 0)}%\n"
                                f"• Cores: {cpu_info.get('cores', 'N/A')}\n"
                                f"• Frequency: {cpu_info.get('frequency', 'N/A')} GHz\n"
                                f"• Load Average: {cpu_info.get('load_average', 'N/A')}"
                            )
                        elif "memory" in intent_lower or "ram" in intent_lower:
                            # Memory-focused summary
                            virt_mem = memory_info.get("virtual", {})
                            phys_mem = memory_info.get("physical", {})
                            summary = (
                                f"💾 Memory Usage:\n"
                                f"• Virtual: {virt_mem.get('percent_used', 0)}% ({virt_mem.get('used_gb', 'N/A')}GB / {virt_mem.get('total_gb', 'N/A')}GB)\n"
                                f"• Physical: {phys_mem.get('percent_used', 0)}% ({phys_mem.get('used_gb', 'N/A')}GB / {phys_mem.get('total_gb', 'N/A')}GB)\n"
                                f"• Available: {virt_mem.get('available_gb', 'N/A')}GB"
                            )
                        elif "disk" in intent_lower or "storage" in intent_lower:
                            # Disk-focused summary
                            disk_lines = []
                            for drive, info in disk_info.items():
                                disk_lines.append(f"• {drive.upper()}: {info.get('percent_used', 0)}% ({info.get('used_gb', 'N/A')}GB / {info.get('total_gb', 'N/A')}GB)")
                            summary = f"💿 Disk Usage:\n" + "\n".join(disk_lines) if disk_lines else "💿 Disk information unavailable"
                        elif "network" in intent_lower:
                            # Network-focused summary
                            summary = (
                                f"🌐 Network Activity:\n"
                                f"• Upload: {network_info.get('bytes_sent_per_sec', 0):.1f}KB/s\n"
                                f"• Download: {network_info.get('bytes_recv_per_sec', 0):.1f}KB/s\n"
                                f"• Total Sent: {network_info.get('bytes_sent_total', 0):.1f}MB\n"
                                f"• Total Received: {network_info.get('bytes_recv_total', 0):.1f}MB"
                            )
                        else:
                            # Default comprehensive summary
                            cpu_pct = cpu_info.get("percent_total", 0)
                            mem_pct = ((memory_info.get("virtual", {})).get("percent_used", 0))
                            temp = temp_info.get("max_temp", "N/A")
                            
                            summary = (
                                f"🖥️ System Health Report:\n"
                                f"• CPU: {cpu_pct}% | RAM: {mem_pct}% | Temp: {temp}°C\n"
                                f"• Disk: {((disk_info.get('c', {})).get('percent_used', 0)) if disk_info.get('c') else 0}% used\n"
                                f"• Network: ↑{network_info.get('bytes_sent_per_sec', 0):.1f}KB/s ↓{network_info.get('bytes_recv_per_sec', 0):.1f}KB/s"
                            )
                    else:
                        # Fallback to simple format
                        summary = f"{agent.name}: {len(plan.actions)} actions ready"
                        
                except Exception as e:
                    logger.warning(f"[PLANNER] Failed to generate detailed summary: {e}")
                    summary = f"{agent.name}: system analysis complete"

                # Return a non-executable step so the Desktop app can surface the result
                # without attempting UI automation / recovery.
                step = {
                    "action": "conversation",
                    "content": summary or f"{agent.name}: plan ready ({len(plan.actions)} actions)",
                }

                logger.info(f"[PLANNER] Agent plan ready with {len(plan.actions)} actions")
                return [step]
                    
    except Exception as e:
        logger.warning(f"[PLANNER] Agent routing failed: {e}, continuing with LLM...")
    
    # ===== Step 2: Check Plan Cache =====
    cache = get_plan_cache()
    cached_plan = cache.get(command)
    if cached_plan:
        logger.info(f"[PLANNER] CACHE HIT! Skipping LLM call")
        logger.info(f"[PLANNER] Returning {len(cached_plan)} cached steps")
        return cached_plan
    
    # ===== Step 3: Get Context for LLM =====
    context = get_context_for_llm(session_id)
    
    # ===== Step 4: Analyze Intent with LLM =====
    logger.info(f"[PLANNER] Cache miss - calling LLM to analyze intent...")
    plan = await analyze_command(command, context)
    
    
    logger.info(f"[PLANNER] LLM Response: intent={plan.get('intent')}, confidence={plan.get('confidence')}")
    logger.info(f"[PLANNER] LLM reasoning: {plan.get('reasoning', 'N/A')}")
    
    # Check confidence threshold
    if plan.get("confidence", 0) < 0.5:
        logger.warning(f"[PLANNER] Low confidence ({plan.get('confidence')}), plan may be unreliable")
    
    # Check for actions - if we have actions, USE THEM even if intent is "unclear"
    actions = plan.get("actions", [])
    logger.info(f"[PLANNER] LLM returned {len(actions)} actions")
    for i, action in enumerate(actions):
        logger.info(f"[PLANNER]   Action {i+1}: {action}")
    
    if not actions:
        logger.warning(f"[PLANNER] LLM returned no actions, returning empty plan")
        return []
    
    # ===== Step 5: Convert to Executor Steps =====
    executor_steps = convert_plan_to_executor_steps(plan)
    
    logger.info(f"[PLANNER] Generated {len(executor_steps)} executor steps:")
    for i, step in enumerate(executor_steps):
        logger.info(f"[PLANNER]   Step {i+1}: {step.get('action')} | {step}")
    
    # ===== Step 6: Cache Successful Plan =====
    if executor_steps and len(executor_steps) > 0:
        cache.put(command, executor_steps)
    
    # ===== Step 7: Update Context =====
    if executor_steps:
        # Update with first action for context tracking
        update_session(session_id, command, executor_steps[0])
    
    logger.info(f"[PLANNER] ========== DONE ==========")
    return executor_steps


def mark_ambiguous_targets(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mark steps that have ambiguous targets requiring vision-based resolution.
    
    Examples of ambiguous: "any video", "first result", "a button"  
    Examples of specific: "Save", "File > Open", "Submit"
    
    Args:
        steps: List of executor steps
        
    Returns:
        Same steps with 'requires_vision_targeting' flag added where needed
    """
    from app.agent.verification_strategy import is_ambiguous_target
    
    # Actions that ALWAYS need vision (inherently ambiguous)
    ALWAYS_VISION_ACTIONS = ["click_element", "find_and_click", "vision_guided"]
    
    # Actions that MAY need vision if target is ambiguous or no coords
    VISION_CANDIDATE_ACTIONS = ["click", "double_click", "right_click"]
    
    for step in steps:
        # Check target and content fields for ambiguity
        target = step.get("target", "") or ""
        content = step.get("content", "") or ""
        action = step.get("action", "")
        
        # click_element and find_and_click ALWAYS need vision
        # They are inherently meant for "find something and click it"
        if action in ALWAYS_VISION_ACTIONS:
            step["requires_vision_targeting"] = True
            logger.info(f"[PLANNER] Vision required (always): {action} → '{target}'")
            continue
        
        # For standard clicks, check if target is ambiguous
        if action in VISION_CANDIDATE_ACTIONS:
            if is_ambiguous_target(target) or is_ambiguous_target(content):
                step["requires_vision_targeting"] = True
                logger.info(f"[PLANNER] Vision required (ambiguous target): {action} → '{target or content}'")
                continue
            
            # If a click has no coordinates, it needs vision
            has_coords = step.get("x") is not None and step.get("y") is not None
            if not has_coords and target:
                step["requires_vision_targeting"] = True
                logger.info(f"[PLANNER] Vision required (no coords): {action} → '{target}'")
    
    return steps


async def plan_command_with_fallback(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Plan command with LLM. Returns vision-guided plan if LLM fails.
    
    NO DETERMINISTIC FALLBACK - removed to prevent bad multi-step parsing.
    Instead, returns a vision-guided plan that will use screen analysis.
    """
    logger.info(f"[PLANNER] plan_command_with_fallback called for: {command}")
    logger.info(f"[PLANNER] USE_LLM_FIRST={USE_LLM_FIRST}")
    
    # Try LLM-first planning (Gemini → Groq)
    if USE_LLM_FIRST:
        try:
            logger.info("[PLANNER] Calling plan_command...")
            steps = await plan_command(command, session_id)
            logger.info(f"[PLANNER] plan_command returned {len(steps)} steps")
            
            if steps:
                # Mark any steps with ambiguous targets for vision resolution
                steps = mark_ambiguous_targets(steps)
                return steps
                
            logger.warning(f"[PLANNER] LLM returned empty plan")
        except Exception as e:
            logger.error(f"[PLANNER] LLM planning error: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("[PLANNER] USE_LLM_FIRST is False!")
    
    # ============================================================
    # NO DETERMINISTIC FALLBACK - Return vision-guided plan instead
    # ============================================================
    logger.warning(f"[PLANNER] LLM failed, returning vision-guided plan")
    
    # Return a special step that tells executor to use vision
    return [{
        "action": "vision_guided",
        "goal": command,
        "requires_vision_targeting": True,
        "reason": "LLM planning failed, using vision-guided execution"
    }]
