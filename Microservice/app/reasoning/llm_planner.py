"""
LLM-First Planner - Unified Planning Pipeline

Replaces if-else logic with:
    Intent Analyzer → Tool Registry → Context Memory → Executor Steps

This is the main entry point for the new architecture.
"""

import os
from typing import List, Dict, Any, Optional

# Feature flag for gradual rollout
USE_LLM_FIRST = os.getenv("USE_LLM_FIRST", "true").lower() == "true"


async def plan_command(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Main planning function - LLM-first with intelligent fallbacks.
    
    Pipeline:
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
    
    print(f"[PLANNER] Processing: '{command}'")
    
    # ===== Step 1: Check Contextual Commands =====
    if is_contextual_command(command):
        resolved = resolve_contextual_command(command, session_id)
        if resolved:
            print(f"[PLANNER] Resolved contextual command: {resolved}")
            # Update context and return
            update_session(session_id, command, resolved)
            return [resolved]
    
    # ===== Step 2: Get Context for LLM =====
    context = get_context_for_llm(session_id)
    
    # ===== Step 3: Analyze Intent with LLM =====
    plan = await analyze_command(command, context)
    
    print(f"[PLANNER] LLM plan: intent={plan.get('intent')}, confidence={plan.get('confidence')}")
    
    # Check confidence threshold
    if plan.get("confidence", 0) < 0.5:
        print(f"[PLANNER] Low confidence ({plan.get('confidence')}), plan may be unreliable")
    
    # Check for unclear intent
    if plan.get("intent") == "unclear" or not plan.get("actions"):
        print(f"[PLANNER] LLM returned unclear intent, returning empty plan")
        return []
    
    # ===== Step 4: Convert to Executor Steps =====
    executor_steps = convert_plan_to_executor_steps(plan)
    
    print(f"[PLANNER] Generated {len(executor_steps)} executor steps")
    for i, step in enumerate(executor_steps):
        print(f"[PLANNER]   Step {i+1}: {step.get('action')}")
    
    # ===== Step 5: Update Context =====
    if executor_steps:
        # Update with first action for context tracking
        update_session(session_id, command, executor_steps[0])
    
    return executor_steps


async def plan_command_with_fallback(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Plan command with fallback to deterministic parser.
    
    This is the safe version that never returns empty if deterministic can handle it.
    """
    from app.api.agent_plan import parse_command, ActionStep
    
    # Try LLM-first planning
    if USE_LLM_FIRST:
        try:
            steps = await plan_command(command, session_id)
            if steps:
                return steps
            print(f"[PLANNER] LLM returned empty, falling back to deterministic")
        except Exception as e:
            print(f"[PLANNER] LLM planning error: {e}")
    
    # Fallback to deterministic
    print(f"[PLANNER] Using deterministic parser")
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
