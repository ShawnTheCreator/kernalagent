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
    2. Analyze intent with LLM (Gemini → Groq)
    3. Convert to executor steps
    4. Update context
    
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
    
    # ===== Step 2: Get Context for LLM =====
    context = get_context_for_llm(session_id)
    
    # ===== Step 3: Analyze Intent with LLM =====
    logger.info(f"[PLANNER] Calling LLM to analyze intent...")
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
    
    # ===== Step 4: Convert to Executor Steps =====
    executor_steps = convert_plan_to_executor_steps(plan)
    
    logger.info(f"[PLANNER] Generated {len(executor_steps)} executor steps:")
    for i, step in enumerate(executor_steps):
        logger.info(f"[PLANNER]   Step {i+1}: {step.get('action')} | {step}")
    
    # ===== Step 5: Update Context =====
    if executor_steps:
        # Update with first action for context tracking
        update_session(session_id, command, executor_steps[0])
    
    logger.info(f"[PLANNER] ========== DONE ==========")
    return executor_steps


async def plan_command_with_fallback(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Plan command with fallback to deterministic parser.
    
    This is the safe version that never returns empty if deterministic can handle it.
    """
    import logging
    logger = logging.getLogger(__name__)
    from app.api.agent_plan import parse_command, ActionStep
    
    logger.info(f"[PLANNER] plan_command_with_fallback called for: {command}")
    logger.info(f"[PLANNER] USE_LLM_FIRST={USE_LLM_FIRST}")
    
    # Try LLM-first planning
    if USE_LLM_FIRST:
        try:
            logger.info("[PLANNER] Calling plan_command...")
            steps = await plan_command(command, session_id)
            logger.info(f"[PLANNER] plan_command returned {len(steps)} steps")
            
            if steps:
                return steps
            logger.warning(f"[PLANNER] LLM returned empty, falling back to deterministic")
        except Exception as e:
            logger.error(f"[PLANNER] LLM planning error: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("[PLANNER] USE_LLM_FIRST is False!")
    
    # Fallback to deterministic
    logger.warning(f"[PLANNER] Using deterministic parser - THIS IS THE BUG")
    deterministic_steps = parse_command(command)
    
    # Convert ActionStep objects to dicts
    return [
        {
            "action": s.action,
            "target": s.target,
            "url": s.url,
            "query": s.query,
            "content": s.content,
            "amount": s.amount,
            "x": s.x,
            "y": s.y,
        }
        for s in deterministic_steps
    ]
