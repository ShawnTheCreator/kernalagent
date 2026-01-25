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
                
                # Convert agent plan to executor steps format
                agent_steps = []
                for action in plan.actions:
                    # Agent actions are in dict format
                    step = {
                        "action": "agent_task",
                        "agent": agent.name,
                        "plan_id": plan.plan_id,
                        "requires_approval": plan.requires_approval,
                        "estimated_impact": plan.estimated_impact,
                        "content": f"Agent {agent.name} has {len(plan.actions)} actions pending approval",
                    }
                    agent_steps.append(step)
                    break  # Return single meta-step for now
                
                if agent_steps:
                    logger.info(f"[PLANNER] Agent plan ready with {len(plan.actions)} actions")
                    return agent_steps
                    
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
