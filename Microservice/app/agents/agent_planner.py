"""
Agent Planner - LLM-based router for on-demand/permission-based agents.

This integrates with the existing LLM planner to:
1. Check if an existing skill handles the intent
2. Use LLM to determine if a specialized agent should handle it
3. Route to the appropriate agent or fall back to general planning

This handles ON_DEMAND agents. CONTINUOUS agents are handled by Control Tower.
"""

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent, ActionPlan
from app.agents.agent_registry import get_registry
from app.db.memory_repo import get_memory

logger = logging.getLogger(__name__)


# Keywords that suggest specific agents
AGENT_KEYWORDS = {
    "JANITOR_AGENT": [
        "clean", "cleanup", "organize", "declutter", "mess",
        "downloads", "desktop", "temp", "temporary", "cache",
        "delete old", "free space", "disk space", "storage",
        "sort files", "file management",
        # Add scan-related keywords
        "scan", "check", "analyze", "examine", "inspect",
        "look at", "review", "search", "find"
    ],
    "RECOVERY_AGENT": [
        "undo", "oops", "restore", "recover", "fix", 
        "bring back", "accidental", "mistake", "recycle bin", 
        "trash", "go back", "revert"
    ],
    # Future agents can be added here
    # "BACKUP_AGENT": ["backup", "sync", "restore", ...],
}


async def should_route_to_agent(intent: str) -> Optional[str]:
    """
    Check if the intent should be handled by a specialized agent.
    
    Args:
        intent: User's intent string
        
    Returns:
        Agent name if a match is found, None otherwise
    """
    intent_lower = intent.lower()
    
    for agent_name, keywords in AGENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in intent_lower)
        # More flexible matching:
        # - Require 2 matches for general keywords
        # - Require 1 match for strong keywords (scan, clean, organize)
        strong_keywords = ["scan", "clean", "organize", "cleanup", "declutter"]
        has_strong_match = any(kw in intent_lower for kw in strong_keywords)
        
        if (has_strong_match and matches >= 1) or (matches >= 2):
            logger.info(f"[AgentPlanner] Intent matches {agent_name} ({matches} keywords)")
            return agent_name
    
    return None


async def get_agent_for_intent(intent: str) -> Optional[BaseAgent]:
    """
    Find and return the agent that should handle this intent.
    
    Args:
        intent: User's intent string
        
    Returns:
        BaseAgent instance or None
    """
    agent_name = await should_route_to_agent(intent)
    if agent_name is None:
        return None
    
    registry = get_registry()
    agent = registry.get(agent_name)
    
    if agent is None:
        logger.warning(f"[AgentPlanner] Agent {agent_name} not registered")
        return None
    
    return agent


async def plan_with_agent(
    intent: str,
    context: Optional[dict] = None
) -> Optional[ActionPlan]:
    """
    Use an agent to create a plan for the given intent.
    
    This is called by the LLM planner when an agent match is detected.
    
    Args:
        intent: User's intent
        context: Optional context (session, etc.)
        
    Returns:
        ActionPlan from the agent, or None if no agent matched
    """
    agent = await get_agent_for_intent(intent)
    if agent is None:
        return None
    
    logger.info(f"[AgentPlanner] Routing to {agent.name} for: {intent}")
    
    try:
        # Run agent's analyze -> plan lifecycle
        analysis_context = context or {}
        analysis_context["intent"] = intent
        
        analysis = await agent.analyze(analysis_context)
        plan = await agent.plan(analysis)
        
        logger.info(f"[AgentPlanner] Agent {agent.name} created plan with {len(plan.actions)} actions")
        
        return plan
        
    except Exception as e:
        logger.error(f"[AgentPlanner] Error running agent {agent.name}: {e}")
        return None


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
    LLM-based router for on-demand agents.
    
    Integrates with the existing planning pipeline to route
    requests to specialized agents when appropriate.
    
    Usage:
        planner = AgentPlanner()
        plan = await planner.plan("clean up my downloads", session_id)
    """
    
    def __init__(self):
        self._registry = get_registry()
    
    async def plan(
        self,
        intent: str,
        session_id: Optional[str] = None,
        context: Optional[dict] = None
    ) -> Optional[ActionPlan]:
        """
        Plan a user intent, checking for agent matches.
        
        Pipeline:
        1. Check if existing skill handles this (skills have priority)
        2. Check if an agent should handle this
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
        
        # Step 2: Check for agent match
        agent = await get_agent_for_intent(intent)
        if agent is None:
            logger.debug("[AgentPlanner] No agent match")
            return None
        
        # Step 3: Delegate to agent
        try:
            ctx = context or {}
            ctx["session_id"] = session_id
            ctx["intent"] = intent
            
            analysis = await agent.analyze(ctx)
            plan = await agent.plan(analysis)
            
            logger.info(f"[AgentPlanner] Created plan via {agent.name}")
            return plan
            
        except Exception as e:
            logger.error(f"[AgentPlanner] Agent error: {e}")
            return None
    
    def get_available_agents(self) -> list[dict]:
        """Get info about all available agents."""
        return self._registry.list_info()
