"""
Intelligent Agent Router - LLM-based agent selection and routing.

Replaces hardcoded keyword matching with intelligent LLM-based agent selection.
Uses agent triggers, specializations, and priorities from the registry.
"""

import logging
from typing import Optional, Dict, List, Tuple
from app.agents.base_agent import BaseAgent, ActionPlan
from app.agents.agent_registry import get_registry
from app.core.config import settings
from google.generativeai import GenerativeModel
import json

logger = logging.getLogger(__name__)


class IntelligentRouter:
    """
    LLM-powered intelligent agent router.
    
    Uses Gemini to analyze user intent and select the best agent
    based on agent capabilities, triggers, and priorities.
    """
    
    def __init__(self):
        self._registry = get_registry()
        self._llm = GenerativeModel(settings.MODEL_ID) if settings.GEMINI_API_KEY else None
        self._agent_cache = {}  # Cache agent info for performance
        self._cache_ttl = 300  # 5 minutes cache
    
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
        
        # Get fresh agent info if cache is stale
        await self._refresh_agent_cache()
        
        # Use LLM for intelligent routing
        if self._llm:
            agent_name = await self._llm_route_intent(intent, context)
        else:
            # Fallback to trigger-based routing
            agent_name = await self._trigger_based_route(intent)
        
        if not agent_name:
            logger.info("[IntelligentRouter] No suitable agent found")
            return None
        
        # Get agent instance
        agent = self._registry.get(agent_name)
        if not agent:
            logger.warning(f"[IntelligentRouter] Agent {agent_name} not found in registry")
            return None
        
        logger.info(f"[IntelligentRouter] Routed to {agent_name} for: {intent}")
        return agent
    
    async def _llm_route_intent(self, intent: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Use LLM to intelligently select the best agent for the intent.
        
        Args:
            intent: User's natural language intent
            context: Optional context
            
        Returns:
            Best matching agent name or None
        """
        try:
            # Prepare agent information for LLM
            agent_info = self._prepare_agent_info()
            
            # Create routing prompt
            prompt = self._create_routing_prompt(intent, agent_info, context)
            
            # Get LLM decision
            response = await self._llm.generate_content_async(prompt)
            decision = self._parse_llm_response(response.text)
            
            if decision:
                logger.info(f"[IntelligentRouter] LLM selected: {decision['agent']} (confidence: {decision['confidence']})")
                return decision['agent']
            
        except Exception as e:
            logger.error(f"[IntelligentRouter] LLM routing failed: {e}")
        
        return None
    
    async def _trigger_based_route(self, intent: str) -> Optional[str]:
        """
        Fallback routing using agent triggers and priorities.
        
        Args:
            intent: User's natural language intent
            
        Returns:
            Best matching agent name or None
        """
        intent_lower = intent.lower()
        best_match = None
        best_score = 0
        
        for agent_name, agent_data in self._agent_cache.items():
            triggers = agent_data.get('triggers', [])
            score = 0
            
            for trigger in triggers:
                if trigger.trigger_type == "user_intent":
                    # Calculate match score based on trigger condition
                    condition = trigger.condition.lower()
                    priority = trigger.priority
                    
                    # Simple keyword matching for fallback
                    keywords = condition.split()
                    matches = sum(1 for kw in keywords if kw in intent_lower)
                    
                    # Weight matches by priority
                    if matches > 0:
                        score += (matches * priority) / 10.0
            
            if score > best_score:
                best_score = score
                best_match = agent_name
        
        return best_match if best_score > 0 else None
    
    def _prepare_agent_info(self) -> str:
        """
        Prepare agent information for LLM consumption.
        
        Returns:
            Formatted string with agent capabilities
        """
        agent_descriptions = []
        
        for agent_name, agent_data in self._agent_cache.items():
            specialization = agent_data.get('specialization', '')
            agent_type = agent_data.get('type', '')
            triggers = agent_data.get('triggers', [])
            
            # Extract user intent triggers
            user_triggers = [
                t.get('condition', '') for t in triggers 
                if t.get('trigger_type') == 'user_intent'
            ]
            
            description = f"""
{agent_name}:
- Type: {agent_type}
- Specialization: {specialization}
- Triggers: {', '.join(user_triggers)}
"""
            agent_descriptions.append(description)
        
        return '\n'.join(agent_descriptions)
    
    def _create_routing_prompt(self, intent: str, agent_info: str, context: Optional[Dict] = None) -> str:
        """
        Create LLM prompt for agent routing decision.
        
        Args:
            intent: User's intent
            agent_info: Formatted agent information
            context: Optional context
            
        Returns:
            LLM prompt string
        """
        context_info = ""
        if context:
            context_info = f"\nContext: {json.dumps(context, indent=2)}"
        
        prompt = f"""You are an intelligent agent router for a PC automation system. 

Given a user intent, select the best agent to handle it.

AVAILABLE AGENTS:
{agent_info}

USER INTENT: "{intent}"
{context_info}

Analyze the intent and select the most appropriate agent. Consider:
1. Agent specialization and capabilities
2. Trigger conditions that match the intent
3. Agent type (hybrid agents can handle more tasks)

Respond with a JSON object:
{{
    "agent": "AGENT_NAME",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this agent was chosen"
}}

If no agent is suitable, respond with:
{{"agent": null, "confidence": 0.0, "reasoning": "No suitable agent found"}}"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse LLM response to extract routing decision.
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            Parsed decision dictionary or None
        """
        try:
            # Extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = response_text[start:end]
                decision = json.loads(json_str)
                
                # Validate decision structure
                if 'agent' in decision and 'confidence' in decision:
                    return decision
            
        except Exception as e:
            logger.error(f"[IntelligentRouter] Failed to parse LLM response: {e}")
        
        return None
    
    async def _refresh_agent_cache(self):
        """Refresh agent information cache if needed."""
        agents = self._registry.get_all()
        logger.info(f"[IntelligentRouter] Found {len(agents)} agents in registry")
        
        for agent in agents:
            logger.info(f"[IntelligentRouter] Caching agent: {agent.name}")
            agent_info = agent.get_info()
            # Convert agent_info to dict and add triggers
            agent_dict = agent_info.copy() if isinstance(agent_info, dict) else agent_info.model_dump()
            agent_dict['triggers'] = agent.get_triggers()
            self._agent_cache[agent.name] = agent_dict
            logger.info(f"[IntelligentRouter] Cached {agent.name} with {len(agent_dict.get('triggers', []))} triggers")
        
        logger.debug(f"[IntelligentRouter] Cached {len(self._agent_cache)} agents")
    
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
            "cached_agents": len(self._agent_cache),
            "llm_available": self._llm is not None,
            "cache_ttl": self._cache_ttl,
            "agents": list(self._agent_cache.keys())
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
