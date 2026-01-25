"""
Agent Registry - Central discovery and registration for all agents.

Provides a singleton registry that:
- Auto-discovers agents at startup
- Provides lookup by name, type, or trigger
"""

from typing import Optional
import logging

from app.agents.base_agent import BaseAgent, AgentType

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all Hive Mind agents.
    
    Usage:
        registry = get_registry()
        registry.register(JanitorAgent())
        agent = registry.get("JANITOR_AGENT")
    """
    
    _instance: Optional["AgentRegistry"] = None
    
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._by_type: dict[AgentType, list[str]] = {
            AgentType.CONTINUOUS: [],
            AgentType.ON_DEMAND: [],
            AgentType.HYBRID: [],
        }
    
    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = AgentRegistry()
        return cls._instance
    
    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent.
        
        Args:
            agent: Agent instance to register
        """
        name = agent.name
        if name in self._agents:
            logger.warning(f"Agent {name} already registered, replacing")
        
        self._agents[name] = agent
        self._by_type[agent.agent_type].append(name)
        logger.info(f"Registered agent: {name} ({agent.agent_type.value})")
    
    def unregister(self, name: str) -> bool:
        """Unregister an agent by name."""
        if name not in self._agents:
            return False
        
        agent = self._agents.pop(name)
        self._by_type[agent.agent_type].remove(name)
        logger.info(f"Unregistered agent: {name}")
        return True
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name."""
        return self._agents.get(name)
    
    def get_all(self) -> list[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """Get all agents of a specific type."""
        names = self._by_type.get(agent_type, [])
        return [self._agents[n] for n in names if n in self._agents]
    
    def get_continuous_agents(self) -> list[BaseAgent]:
        """Get all continuous/background agents."""
        continuous = self.get_by_type(AgentType.CONTINUOUS)
        hybrid = self.get_by_type(AgentType.HYBRID)
        return continuous + hybrid
    
    def get_on_demand_agents(self) -> list[BaseAgent]:
        """Get all on-demand agents (for LLM routing)."""
        on_demand = self.get_by_type(AgentType.ON_DEMAND)
        hybrid = self.get_by_type(AgentType.HYBRID)
        return on_demand + hybrid
    
    def find_by_intent(self, intent: str) -> list[BaseAgent]:
        """
        Find agents whose triggers might match an intent.
        
        Args:
            intent: User intent string
            
        Returns:
            List of potentially matching agents
        """
        matches = []
        intent_lower = intent.lower()
        
        for agent in self._agents.values():
            for trigger in agent.get_triggers():
                if trigger.trigger_type == "user_intent":
                    # Check if any keywords from condition appear in intent
                    keywords = trigger.condition.lower().split()
                    if any(kw in intent_lower for kw in keywords):
                        matches.append(agent)
                        break
        
        return matches
    
    def list_info(self) -> list[dict]:
        """Get info for all agents (for API responses)."""
        return [agent.get_info() for agent in self._agents.values()]


# Singleton accessor
def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return AgentRegistry.get_instance()
