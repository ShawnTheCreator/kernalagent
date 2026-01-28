"""
Agent Planner - Enhanced with Intelligent LLM-based routing.

This integrates with the existing LLM planner to:
1. Check if an existing skill handles the intent
2. Use intelligent LLM routing to determine the best agent
3. Route to the appropriate agent or fall back to general planning

This handles ON_DEMAND agents. CONTINUOUS agents are handled by Control Tower.
"""

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent, ActionPlan
from app.agents.agent_registry import get_registry
from app.agents.intelligent_router import get_intelligent_router
from app.db.memory_repo import get_memory

logger = logging.getLogger(__name__)


async def should_route_to_agent(intent: str, context: Optional[dict] = None) -> Optional[str]:
    """Return the best matching agent name for this intent, if any.

    This function is used by the LLM-first planner (Step 1.5) to decide whether to
    delegate planning to a specialized agent.
    """
    router = get_intelligent_router()
    return await router._trigger_based_route(intent)


async def get_agent_for_intent(intent: str, context: Optional[dict] = None) -> Optional[BaseAgent]:
    """
    Find and return the agent that should handle this intent using intelligent routing.
    
    Args:
        intent: User's intent string
        context: Optional context for routing
        
    Returns:
        BaseAgent instance or None
    """
    router = get_intelligent_router()
    return await router.route_to_agent(intent, context)


async def plan_with_agent(
    intent: str,
    context: Optional[dict] = None
) -> Optional[ActionPlan]:
    """
    Use intelligent routing to create a plan for the given intent.
    
    This uses the LLM-powered intelligent router to select and execute the best agent.
    
    Args:
        intent: User's intent
        context: Optional context (session, etc.)
        
    Returns:
        ActionPlan from the best-matching agent, or None if no agent matched
    """
    router = get_intelligent_router()
    return await router.execute_agent_plan(intent, context)


async def check_skill_exists_for_intent(intent: str, user_id: str = "default_user") -> bool:
    """
    Check if an existing skill handles this intent.
    
    Skills take priority over agents for learned behaviors.
    
    Args:
        intent: User's intent
        user_id: User ID for personalized memory lookup
        
    Returns:
        True if a skill exists with good match
    """
    try:
        from app.agent.decision_engine import select_best_skill
        from app.db.skills_repo import get_all_skills
        
        skills = get_all_skills()
        
        # v3: Fetch user LTM (frequent skills) for personalized boost
        user_memory = get_memory(user_id, "long_term") if user_id else None
        
        best_match = select_best_skill(intent, skills, user_context=user_memory)
        
        if best_match and best_match.get('similarity', 0) > 0.5:
            logger.info(f"[AgentPlanner] Found existing skill: {best_match.get('skill', {}).get('name')} (Score: {best_match.get('score', 0):.2f})")
            if best_match.get('is_frequent'):
                 logger.info(f"[AgentPlanner] ✨ Personalized match (Frequent Skill)")
            return True
            
    except Exception as e:
        logger.warning(f"[AgentPlanner] Error checking skills: {e}")
    
    return False


class AgentPlanner:
    """
    Enhanced LLM-based router with intelligent agent selection.
    
    Uses the IntelligentRouter to analyze user intent and select the best agent
    based on capabilities, triggers, and priorities from the registry.
    
    Usage:
        planner = AgentPlanner()
        plan = await planner.plan("check system health", session_id)
    """
    
    def __init__(self):
        self._registry = get_registry()
        self._intelligent_router = get_intelligent_router()
    
    async def plan(
        self,
        intent: str,
        session_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Optional[ActionPlan]:
        """
        Plan a user intent using intelligent agent routing.
        
        Pipeline:
        1. Check if existing skill handles this (skills have priority)
        2. Use intelligent LLM routing to select best agent
        3. If agent, delegate to agent.analyze() -> agent.plan()
        4. Return plan or None
        
        Args:
            intent: User's natural language intent
            session_id: Optional session for context
            context: Optional additional context
            
        Returns:
            ActionPlan if an agent handles it, None otherwise
        """
        logger.info(f"[AgentPlanner] Planning: {intent}")
        
        # Extract user_id for memory lookup
        user_id = "default_user"
        if context and "user_id" in context:
            user_id = context["user_id"]
        
        # Step 1: Check for existing skill
        if await check_skill_exists_for_intent(intent, user_id):
            logger.info("[AgentPlanner] Skill exists, using general planner")
            return None  # Let the general planner handle it
        
        # Step 2: Use intelligent routing to select best agent
        try:
            ctx = context or {}
            ctx["session_id"] = session_id
            ctx["intent"] = intent
            
            plan = await self._intelligent_router.execute_agent_plan(intent, ctx)
            
            if plan:
                logger.info(f"[AgentPlanner] Created plan via intelligent routing")
                return plan
            
        except Exception as e:
            logger.error(f"[AgentPlanner] Intelligent routing failed: {e}")
        
        logger.debug("[AgentPlanner] No agent match found")
        return None
    
    def get_available_agents(self) -> list[dict]:
        """Get info about all available agents."""
        return self._registry.list_info()
    
    def get_router_stats(self) -> dict:
        """Get intelligent router statistics."""
        return self._intelligent_router.get_routing_stats()
