"""
Intelligent Agent Router - LLM-based agent selection and routing.

Replaces hardcoded keyword matching with intelligent LLM-based agent selection.
Uses agent triggers, specializations, and priorities from the registry.
"""

import logging
from typing import Optional, Dict, Any

from app.agents.base_agent import BaseAgent, ActionPlan
from app.agents.agent_registry import get_registry

logger = logging.getLogger(__name__)


class IntelligentRouter:
    """
    LLM-powered intelligent agent router.
    
    Uses Gemini to analyze user intent and select the best agent
    based on agent capabilities, triggers, and priorities.
    """
    
    def __init__(self):
        # Deterministic routing based on agents' declared triggers.
        # This avoids hardcoded keyword maps and avoids any LLM quota failures.
        pass
    
    async def route_to_agent(self, intent: str, context: Optional[Dict] = None) -> Optional[BaseAgent]:
        """
        Intelligently route user intent to the best matching agent.
        
        Args:
            intent: User's natural language intent
            context: Optional context (session, user_id, etc.)
            
        Returns:
            Best matching BaseAgent or None
        """
        logger.info(f"[IntelligentRouter] Routing intent: {intent}")
        
        agent_name = await self._trigger_based_route(intent)
        
        if not agent_name:
            logger.info("[IntelligentRouter] No suitable agent found")
            return None
        
        # Get agent instance
        agent = get_registry().get(agent_name)
        if not agent:
            logger.warning(f"[IntelligentRouter] Agent {agent_name} not found in registry")
            return None
        
        logger.info(f"[IntelligentRouter] Routed to {agent_name} for: {intent}")
        return agent
    
    async def _trigger_based_route(self, intent: str) -> Optional[str]:
        """
        Fallback routing using agent triggers and priorities.
        
        Args:
            intent: User's natural language intent
            
        Returns:
            Best matching agent name or None
        """
        intent_lower = intent.lower()
        registry = get_registry()

        best_match: Optional[str] = None
        best_score: float = 0.0

        for agent in registry.get_all():
            score = 0.0

            for trigger in agent.get_triggers():
                if trigger.trigger_type != "user_intent":
                    continue

                condition = (trigger.condition or "").lower()
                # Split by spaces; triggers are authored as keyword bags.
                keywords = [k for k in condition.split() if k]
                matches = sum(1 for kw in keywords if kw in intent_lower)

                if matches > 0:
                    score += (matches * float(trigger.priority))

            if score > best_score:
                best_score = score
                best_match = agent.name

        return best_match if best_score > 0 else None
    
    async def execute_agent_plan(self, intent: str, context: Optional[Dict] = None) -> Optional[ActionPlan]:
        """
        Route to agent and execute its planning lifecycle.
        
        Args:
            intent: User's intent
            context: Optional context
            
        Returns:
            ActionPlan from selected agent or None
        """
        agent = await self.route_to_agent(intent, context)
        if not agent:
            return None
        
        try:
            # Execute agent's analyze -> plan lifecycle
            analysis_context = context or {}
            analysis_context["intent"] = intent
            
            analysis = await agent.analyze(analysis_context)
            plan = await agent.plan(analysis)
            
            logger.info(f"[IntelligentRouter] {agent.name} created plan with {len(plan.actions)} actions")
            return plan
            
        except Exception as e:
            logger.error(f"[IntelligentRouter] Agent execution failed: {e}")
            return None
    
    def get_routing_stats(self) -> Dict:
        """Get router statistics and cache info."""
        return {
            "mode": "trigger_based",
            "registered_agents": [a.name for a in get_registry().get_all()],
        }


# Global router instance
_intelligent_router = None

def get_intelligent_router() -> IntelligentRouter:
    """Get or create the global intelligent router instance."""
    global _intelligent_router
    if _intelligent_router is None:
        _intelligent_router = IntelligentRouter()
    return _intelligent_router


# Convenience functions for backward compatibility
async def route_to_agent(intent: str, context: Optional[Dict] = None) -> Optional[BaseAgent]:
    """Route intent to best matching agent."""
    router = get_intelligent_router()
    return await router.route_to_agent(intent, context)


async def plan_with_agent(intent: str, context: Optional[Dict] = None) -> Optional[ActionPlan]:
    """Create plan using intelligent agent routing."""
    router = get_intelligent_router()
    return await router.execute_agent_plan(intent, context)
