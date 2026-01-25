"""
Base Agent - Abstract foundation for all Hive Mind agents.

All specialized agents (Janitor, etc.) inherit from BaseAgent and implement
the core lifecycle: analyze() -> plan() -> execute()

Agent Types:
- CONTINUOUS: Runs in background, triggered by system state (Control Tower)
- ON_DEMAND: Triggered by user intent (LLM Planner)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class AgentType(str, Enum):
    """Type of agent determines how it's routed."""
    CONTINUOUS = "continuous"    # Background agent (Control Tower)
    ON_DEMAND = "on_demand"      # User-triggered (LLM Planner)
    HYBRID = "hybrid"            # Both modes


class AgentTrigger(BaseModel):
    """Defines when an agent should be activated."""
    trigger_type: str  # "system_pulse", "user_intent", "scheduled"
    condition: str     # e.g., "disk_usage > 90%", "user says 'clean'"
    priority: int = Field(default=5, ge=1, le=10)  # 1=low, 10=urgent


class AnalysisResult(BaseModel):
    """Result of an agent's analysis phase."""
    agent_name: str
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    findings: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    severity: str = "info"  # info, warning, critical
    
    
class ActionPlan(BaseModel):
    """A plan of actions to be executed by the agent."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    analysis_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = True
    approved: bool = False
    estimated_impact: str = ""  # e.g., "2.5GB space recovered"
    

class ExecutionResult(BaseModel):
    """Result of executing a plan."""
    plan_id: str
    agent_name: str
    status: str  # "success", "partial", "failed"
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    actions_completed: int = 0
    actions_failed: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class AgentStatus(BaseModel):
    """Current status of an agent."""
    name: str
    agent_type: AgentType
    is_running: bool = False
    last_run: Optional[datetime] = None
    current_task: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all Hive Mind agents.
    
    Lifecycle:
    1. analyze() - Survey the environment, gather data
    2. plan() - Create an action plan based on analysis
    3. execute() - Execute the approved plan
    
    Subclasses must implement all abstract methods.
    """
    
    # Agent identity (must be set by subclass)
    name: str = "UNNAMED_AGENT"
    specialization: str = "No specialization defined"
    agent_type: AgentType = AgentType.ON_DEMAND
    
    def __init__(self):
        self._status = AgentStatus(
            name=self.name,
            agent_type=self.agent_type
        )
    
    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status
    
    @abstractmethod
    async def analyze(self, context: dict) -> AnalysisResult:
        """
        Survey the environment and gather data.
        
        Args:
            context: Environment context (paths, settings, etc.)
            
        Returns:
            AnalysisResult with findings and recommendations
        """
        pass
    
    @abstractmethod
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """
        Create an action plan based on analysis.
        
        Args:
            analysis: Result from analyze()
            
        Returns:
            ActionPlan with proposed actions (requires user approval)
        """
        pass
    
    @abstractmethod
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """
        Execute an approved action plan.
        
        Args:
            plan: Approved ActionPlan
            
        Returns:
            ExecutionResult with metrics and status
        """
        pass
    
    @abstractmethod
    def get_triggers(self) -> list[AgentTrigger]:
        """
        Return conditions that trigger this agent.
        
        Returns:
            List of AgentTrigger defining activation conditions
        """
        pass
    
    def get_info(self) -> dict:
        """Get agent info for API responses."""
        return {
            "name": self.name,
            "specialization": self.specialization,
            "type": self.agent_type.value,
            "triggers": [t.model_dump() for t in self.get_triggers()],
            "status": self._status.model_dump()
        }
    
    async def on_start(self) -> None:
        """Called when agent starts (for background agents)."""
        self._status.is_running = True
        self._status.current_task = "Starting..."
        
    async def on_stop(self) -> None:
        """Called when agent stops."""
        self._status.is_running = False
        self._status.current_task = None
        self._status.last_run = datetime.utcnow()
