"""
Kernel Agent - Hive Mind Agent Framework

This package contains specialized agents that extend the AI's capabilities
for autonomous, domain-specific tasks.

Architecture:
- Control Tower: Routes continuous/background agents based on system state
- LLM Planner: Routes permission-based agents based on user intent
"""

from app.agents.base_agent import BaseAgent, AgentTrigger, AgentType
from app.agents.agent_registry import AgentRegistry, get_registry
from app.agents.agent_router import ControlTower
from app.agents.agent_planner import AgentPlanner

__all__ = [
    "BaseAgent",
    "AgentTrigger", 
    "AgentType",
    "AgentRegistry",
    "get_registry",
    "ControlTower",
    "AgentPlanner",
]
