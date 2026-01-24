"""
Control Tower (Agent Router) - Routes continuous/background agents.

The Control Tower is responsible for:
- Monitoring system pulse (disk usage, idle time, etc.)
- Starting/stopping background agents based on triggers
- Managing agent lifecycle for continuous agents ONLY

Permission-based agents are routed by the LLM Planner, not here.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent, AgentType, AnalysisResult
from app.agents.agent_registry import get_registry

logger = logging.getLogger(__name__)


class SystemPulse(BaseModel):
    """Current system state for trigger evaluation."""
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    user_idle_seconds: int = 0
    downloads_file_count: int = 0
    desktop_file_count: int = 0
    temp_size_mb: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentTask(BaseModel):
    """A task assigned to an agent by the Control Tower."""
    task_id: str
    agent_name: str
    trigger_reason: str
    priority: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ControlTower:
    """
    Routes ONLY continuous/background agents based on system state.
    
    The Control Tower does NOT handle user intent routing - that's the
    LLM Planner's job.
    
    Usage:
        tower = ControlTower()
        await tower.start()  # Start background monitoring
        
        # Or manual tick:
        pulse = await tower.get_system_pulse()
        tasks = await tower.tick(pulse)
    """
    
    def __init__(self):
        self._running = False
        self._tick_interval = 300  # 5 minutes
        self._thresholds = {
            "disk_usage_high": 85.0,  # % usage
            "idle_trigger": 1800,     # 30 min idle
            "downloads_clutter": 50,  # files
            "desktop_clutter": 30,    # files
        }
        self._running_agents: dict[str, asyncio.Task] = {}
    
    async def get_system_pulse(self) -> SystemPulse:
        """
        Gather current system metrics.
        
        Returns:
            SystemPulse with current system state
        """
        import os
        import shutil
        
        pulse = SystemPulse()
        
        try:
            # Disk usage
            user_home = os.path.expanduser("~")
            disk = shutil.disk_usage(user_home)
            pulse.disk_usage_percent = (disk.used / disk.total) * 100
            pulse.disk_free_gb = disk.free / (1024 ** 3)
            
            # Downloads folder
            downloads = os.path.join(user_home, "Downloads")
            if os.path.exists(downloads):
                pulse.downloads_file_count = len([
                    f for f in os.listdir(downloads) 
                    if os.path.isfile(os.path.join(downloads, f))
                ])
            
            # Desktop folder
            desktop = os.path.join(user_home, "Desktop")
            if os.path.exists(desktop):
                pulse.desktop_file_count = len([
                    f for f in os.listdir(desktop)
                    if os.path.isfile(os.path.join(desktop, f))
                ])
            
            # Temp folder size
            temp_dir = os.environ.get("TEMP", os.path.join(user_home, "AppData", "Local", "Temp"))
            if os.path.exists(temp_dir):
                total_size = 0
                for dirpath, _, filenames in os.walk(temp_dir):
                    for f in filenames:
                        try:
                            fp = os.path.join(dirpath, f)
                            total_size += os.path.getsize(fp)
                        except (OSError, PermissionError):
                            pass
                pulse.temp_size_mb = total_size / (1024 * 1024)
                
        except Exception as e:
            logger.error(f"Error gathering system pulse: {e}")
        
        return pulse
    
    async def tick(self, pulse: SystemPulse) -> list[AgentTask]:
        """
        Check if any continuous agents should be triggered.
        
        Called periodically by the background loop or manually.
        
        Args:
            pulse: Current system state
            
        Returns:
            List of tasks to be executed
        """
        tasks = []
        registry = get_registry()
        
        for agent in registry.get_continuous_agents():
            if agent.name in self._running_agents:
                continue  # Already running
            
            should_trigger, reason = self._should_trigger(agent, pulse)
            
            if should_trigger:
                import uuid
                task = AgentTask(
                    task_id=str(uuid.uuid4()),
                    agent_name=agent.name,
                    trigger_reason=reason,
                    priority=5
                )
                tasks.append(task)
                logger.info(f"[ControlTower] Triggering {agent.name}: {reason}")
        
        return tasks
    
    def _should_trigger(self, agent: BaseAgent, pulse: SystemPulse) -> tuple[bool, str]:
        """
        Check if an agent's triggers match current system state.
        
        Returns:
            (should_trigger, reason)
        """
        for trigger in agent.get_triggers():
            if trigger.trigger_type != "system_pulse":
                continue
            
            condition = trigger.condition.lower()
            
            # Check disk usage trigger
            if "disk_usage" in condition:
                if pulse.disk_usage_percent >= self._thresholds["disk_usage_high"]:
                    return True, f"Disk usage at {pulse.disk_usage_percent:.1f}%"
            
            # Check idle trigger
            if "idle" in condition:
                if pulse.user_idle_seconds >= self._thresholds["idle_trigger"]:
                    return True, f"User idle for {pulse.user_idle_seconds}s"
            
            # Check downloads clutter
            if "downloads" in condition:
                if pulse.downloads_file_count >= self._thresholds["downloads_clutter"]:
                    return True, f"Downloads has {pulse.downloads_file_count} files"
            
            # Check desktop clutter
            if "desktop" in condition:
                if pulse.desktop_file_count >= self._thresholds["desktop_clutter"]:
                    return True, f"Desktop has {pulse.desktop_file_count} files"
        
        return False, ""
    
    async def start_agent(self, agent: BaseAgent, task: AgentTask) -> Optional[AnalysisResult]:
        """
        Start a background agent's analysis.
        
        Args:
            agent: Agent to start
            task: Task that triggered the agent
            
        Returns:
            AnalysisResult from the agent
        """
        try:
            await agent.on_start()
            agent._status.current_task = task.trigger_reason
            
            # Run analysis
            context = {
                "trigger_reason": task.trigger_reason,
                "task_id": task.task_id,
            }
            result = await agent.analyze(context)
            
            await agent.on_stop()
            return result
            
        except Exception as e:
            logger.error(f"Error running agent {agent.name}: {e}")
            await agent.on_stop()
            return None
    
    async def start(self) -> None:
        """Start the Control Tower background loop."""
        if self._running:
            return
        
        self._running = True
        logger.info("[ControlTower] Starting background monitoring...")
        
        while self._running:
            try:
                pulse = await self.get_system_pulse()
                tasks = await self.tick(pulse)
                
                # Start any triggered agents
                registry = get_registry()
                for task in tasks:
                    agent = registry.get(task.agent_name)
                    if agent:
                        # Run in background task
                        asyncio.create_task(self.start_agent(agent, task))
                
            except Exception as e:
                logger.error(f"[ControlTower] Tick error: {e}")
            
            await asyncio.sleep(self._tick_interval)
    
    async def stop(self) -> None:
        """Stop the Control Tower."""
        self._running = False
        logger.info("[ControlTower] Stopped")
    
    def get_status(self) -> dict:
        """Get Control Tower status for API."""
        return {
            "running": self._running,
            "tick_interval_seconds": self._tick_interval,
            "thresholds": self._thresholds,
            "running_agents": list(self._running_agents.keys())
        }
