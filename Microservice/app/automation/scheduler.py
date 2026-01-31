"""
Intelligent Scheduling System for Kernal Agent

Provides cron-style scheduling, event-driven triggers, and smart automation.
Supports both time-based and condition-based task execution.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import psutil
import json

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Types of automation triggers."""
    CRON = "cron"
    SYSTEM_EVENT = "system_event"
    FILE_EVENT = "file_event"
    APPLICATION_EVENT = "app_event"
    BATTERY_EVENT = "battery_event"
    NETWORK_EVENT = "network_event"
    USER_PATTERN = "user_pattern"


@dataclass
class ScheduledTask:
    """A scheduled automation task."""
    task_id: str
    name: str
    trigger_type: TriggerType
    trigger_condition: str
    action_plan: List[Dict[str, Any]]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemState:
    """Current system state for trigger evaluation."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    battery_percent: int
    downloads_count: int
    desktop_count: int
    active_app: str
    idle_seconds: int
    network_connected: bool
    timestamp: datetime = field(default_factory=datetime.now)


class CronParser:
    """Simple cron expression parser."""
    
    @staticmethod
    def parse_cron(expression: str) -> Dict[str, Any]:
        """Parse cron expression like '0 9 * * MON'."""
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")
        
        minute, hour, day, month, weekday = parts
        
        return {
            "minute": CronParser._parse_field(minute, 0, 59),
            "hour": CronParser._parse_field(hour, 0, 23),
            "day": CronParser._parse_field(day, 1, 31),
            "month": CronParser._parse_field(month, 1, 12),
            "weekday": CronParser._parse_weekday(weekday)
        }
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field."""
        if field == "*":
            return list(range(min_val, max_val + 1))
        elif "/" in field:
            base, step = field.split("/")
            base_values = CronParser._parse_field(base, min_val, max_val)
            return [v for v in base_values if (v - min_val) % int(step) == 0]
        elif "," in field:
            return [int(x) for x in field.split(",")]
        elif "-" in field:
            start, end = map(int, field.split("-"))
            return list(range(start, end + 1))
        else:
            return [int(field)]
    
    @staticmethod
    def _parse_weekday(field: str) -> List[int]:
        """Parse weekday field, supporting day names."""
        if field == "*":
            return list(range(7))
        
        day_names = {
            "SUN": 0, "MON": 1, "TUE": 2, "WED": 3,
            "THU": 4, "FRI": 5, "SAT": 6
        }
        
        # Replace day names with numbers
        for name, num in day_names.items():
            field = field.replace(name, str(num))
        
        return CronParser._parse_field(field, 0, 6)
    
    @staticmethod
    def should_run(cron_config: Dict[str, Any], dt: datetime) -> bool:
        """Check if cron should run at given datetime."""
        return (
            dt.minute in cron_config["minute"] and
            dt.hour in cron_config["hour"] and
            dt.day in cron_config["day"] and
            dt.month in cron_config["month"] and
            dt.weekday() in cron_config["weekday"]
        )


class SystemMonitor:
    """Monitors system state for event-driven triggers."""
    
    def __init__(self):
        self._last_state: Optional[SystemState] = None
    
    def get_current_state(self) -> SystemState:
        """Get current system state."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('C:' if os.name == 'nt' else '/')
            
            # Get battery info (if available)
            battery_percent = 100
            try:
                battery = psutil.sensors_battery()
                if battery:
                    battery_percent = battery.percent
            except:
                pass
            
            # Get file counts
            downloads_dir = os.path.expanduser("~/Downloads")
            desktop_dir = os.path.expanduser("~/Desktop")
            
            downloads_count = len([f for f in os.listdir(downloads_dir) 
                                 if os.path.isfile(os.path.join(downloads_dir, f))]) if os.path.exists(downloads_dir) else 0
            desktop_count = len([f for f in os.listdir(desktop_dir)
                               if os.path.isfile(os.path.join(desktop_dir, f))]) if os.path.exists(desktop_dir) else 0
            
            # Get active application (simplified)
            active_app = "unknown"
            try:
                # This would need platform-specific implementation
                active_app = "active_window"
            except:
                pass
            
            # Calculate idle time (simplified)
            idle_seconds = 0  # Would need platform-specific implementation
            
            # Check network connectivity
            network_connected = True
            try:
                network_stats = psutil.net_if_stats()
                network_connected = any(stat.isup for stat in network_stats.values())
            except:
                pass
            
            return SystemState(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                battery_percent=battery_percent,
                downloads_count=downloads_count,
                desktop_count=desktop_count,
                active_app=active_app,
                idle_seconds=idle_seconds,
                network_connected=network_connected
            )
            
        except Exception as e:
            logger.error(f"Failed to get system state: {e}")
            return SystemState(
                cpu_percent=0, memory_percent=0, disk_usage_percent=0,
                battery_percent=100, downloads_count=0, desktop_count=0,
                active_app="unknown", idle_seconds=0, network_connected=True
            )
    
    def check_triggers(self, current_state: SystemState, tasks: List[ScheduledTask]) -> List[ScheduledTask]:
        """Check which tasks should be triggered based on system state."""
        triggered_tasks = []
        
        for task in tasks:
            if not task.enabled:
                continue
                
            should_trigger = False
            
            if task.trigger_type == TriggerType.SYSTEM_EVENT:
                should_trigger = self._check_system_trigger(task.trigger_condition, current_state)
            elif task.trigger_type == TriggerType.FILE_EVENT:
                should_trigger = self._check_file_trigger(task.trigger_condition, current_state)
            elif task.trigger_type == TriggerType.BATTERY_EVENT:
                should_trigger = self._check_battery_trigger(task.trigger_condition, current_state)
            elif task.trigger_type == TriggerType.NETWORK_EVENT:
                should_trigger = self._check_network_trigger(task.trigger_condition, current_state)
            
            if should_trigger:
                triggered_tasks.append(task)
        
        self._last_state = current_state
        return triggered_tasks
    
    def _check_system_trigger(self, condition: str, state: SystemState) -> bool:
        """Check system-based triggers."""
        try:
            if "cpu >" in condition:
                threshold = float(condition.split("cpu >")[1].strip().rstrip("%"))
                return state.cpu_percent > threshold
            elif "memory >" in condition:
                threshold = float(condition.split("memory >")[1].strip().rstrip("%"))
                return state.memory_percent > threshold
            elif "disk >" in condition:
                threshold = float(condition.split("disk >")[1].strip().rstrip("%"))
                return state.disk_usage_percent > threshold
            elif "idle >" in condition:
                threshold = int(condition.split("idle >")[1].strip())
                return state.idle_seconds > threshold
        except Exception as e:
            logger.error(f"Error checking system trigger '{condition}': {e}")
        
        return False
    
    def _check_file_trigger(self, condition: str, state: SystemState) -> bool:
        """Check file-based triggers."""
        try:
            if "downloads >" in condition:
                threshold = int(condition.split("downloads >")[1].strip())
                return state.downloads_count > threshold
            elif "desktop >" in condition:
                threshold = int(condition.split("desktop >")[1].strip())
                return state.desktop_count > threshold
        except Exception as e:
            logger.error(f"Error checking file trigger '{condition}': {e}")
        
        return False
    
    def _check_battery_trigger(self, condition: str, state: SystemState) -> bool:
        """Check battery-based triggers."""
        try:
            if "battery <" in condition:
                threshold = int(condition.split("battery <")[1].strip().rstrip("%"))
                return state.battery_percent < threshold
            elif "battery >" in condition:
                threshold = int(condition.split("battery >")[1].strip().rstrip("%"))
                return state.battery_percent > threshold
        except Exception as e:
            logger.error(f"Error checking battery trigger '{condition}': {e}")
        
        return False
    
    def _check_network_trigger(self, condition: str, state: SystemState) -> bool:
        """Check network-based triggers."""
        try:
            if condition == "network_disconnected":
                return not state.network_connected
            elif condition == "network_connected":
                return state.network_connected
        except Exception as e:
            logger.error(f"Error checking network trigger '{condition}': {e}")
        
        return False


class SmartScheduler:
    """Intelligent scheduling system with multiple trigger types."""
    
    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.system_monitor = SystemMonitor()
        self.running = False
        self.check_interval = 60  # Check every minute
        self._task_callbacks: Dict[str, Callable] = {}
    
    def schedule(
        self, 
        name: str,
        trigger_type: TriggerType,
        trigger_condition: str,
        action_plan: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """Schedule a new task."""
        task_id = f"task_{int(time.time() * 1000)}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            action_plan=action_plan,
            metadata=kwargs
        )
        
        # Parse cron expressions for next run time
        if trigger_type == TriggerType.CRON:
            try:
                cron_config = CronParser.parse_cron(trigger_condition)
                task.next_run = self._calculate_next_run(cron_config)
            except Exception as e:
                logger.error(f"Invalid cron expression '{trigger_condition}': {e}")
                return ""
        
        self.tasks.append(task)
        logger.info(f"Scheduled task '{name}' with trigger '{trigger_condition}'")
        return task_id
    
    def schedule_cron(self, cron_expression: str, name: str, action_plan: List[Dict[str, Any]]) -> str:
        """Schedule a cron-based task."""
        return self.schedule(name, TriggerType.CRON, cron_expression, action_plan)
    
    def schedule_system_event(self, condition: str, name: str, action_plan: List[Dict[str, Any]]) -> str:
        """Schedule a system event-based task."""
        return self.schedule(name, TriggerType.SYSTEM_EVENT, condition, action_plan)
    
    def schedule_file_event(self, condition: str, name: str, action_plan: List[Dict[str, Any]]) -> str:
        """Schedule a file event-based task."""
        return self.schedule(name, TriggerType.FILE_EVENT, condition, action_plan)
    
    def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        for i, task in enumerate(self.tasks):
            if task.task_id == task_id:
                self.tasks.pop(i)
                logger.info(f"Unscheduled task {task_id}")
                return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.enabled = True
                return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.enabled = False
                return True
        return False
    
    def get_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return self.tasks.copy()
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a specific task."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        logger.info("SmartScheduler started")
        
        while self.running:
            try:
                await self._check_and_execute()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)  # Short delay on error
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("SmartScheduler stopped")
    
    async def _check_and_execute(self):
        """Check for triggered tasks and execute them."""
        now = datetime.now()
        current_state = self.system_monitor.get_current_state()
        
        # Check cron-based tasks
        for task in self.tasks:
            if not task.enabled or task.trigger_type != TriggerType.CRON:
                continue
            
            if task.next_run and now >= task.next_run:
                await self._execute_task(task)
                
                # Calculate next run time
                try:
                    cron_config = CronParser.parse_cron(task.trigger_condition)
                    task.next_run = self._calculate_next_run(cron_config, now)
                except Exception as e:
                    logger.error(f"Failed to calculate next run for task {task.task_id}: {e}")
        
        # Check event-driven tasks
        triggered_tasks = self.system_monitor.check_triggers(current_state, self.tasks)
        for task in triggered_tasks:
            # Avoid executing the same task too frequently
            if task.last_run and (now - task.last_run).total_seconds() < 300:  # 5 minute cooldown
                continue
            
            await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        logger.info(f"Executing task: {task.name}")
        
        try:
            # Update task stats
            task.last_run = datetime.now()
            task.run_count += 1
            
            # Check max runs
            if task.max_runs and task.run_count >= task.max_runs:
                task.enabled = False
                logger.info(f"Task {task.name} disabled after {task.max_runs} runs")
            
            # Execute the action plan
            await self._execute_action_plan(task.action_plan, task)
            
        except Exception as e:
            logger.error(f"Failed to execute task {task.name}: {e}")
    
    async def _execute_action_plan(self, action_plan: List[Dict[str, Any]], task: ScheduledTask):
        """Execute an action plan."""
        # This would integrate with the main planning system
        logger.info(f"Executing {len(action_plan)} actions for task {task.name}")
        
        for action in action_plan:
            action_type = action.get("action")
            
            if action_type == "agent_task":
                # Execute agent task
                await self._execute_agent_task(action, task)
            elif action_type == "system_command":
                # Execute system command
                await self._execute_system_command(action, task)
            elif action_type == "cleanup":
                # Execute cleanup action
                await self._execute_cleanup_action(action, task)
            else:
                logger.warning(f"Unknown action type: {action_type}")
    
    async def _execute_agent_task(self, action: Dict[str, Any], task: ScheduledTask):
        """Execute an agent task."""
        try:
            from app.agents.agent_registry import get_registry
            
            agent_name = action.get("agent")
            intent = action.get("intent", "")
            
            registry = get_registry()
            agent = registry.get(agent_name)
            
            if agent:
                context = {"intent": intent, "scheduled_task": True}
                analysis = await agent.analyze(context)
                plan = await agent.plan(analysis)
                result = await agent.execute(plan)
                
                logger.info(f"Agent task completed: {result.status}")
            else:
                logger.warning(f"Agent not found: {agent_name}")
                
        except Exception as e:
            logger.error(f"Agent task execution failed: {e}")
    
    async def _execute_system_command(self, action: Dict[str, Any], task: ScheduledTask):
        """Execute a system command."""
        command = action.get("command", "")
        if command:
            logger.info(f"Executing system command: {command}")
            # Implementation would depend on the command execution system
    
    async def _execute_cleanup_action(self, action: Dict[str, Any], task: ScheduledTask):
        """Execute a cleanup action."""
        cleanup_type = action.get("type")
        target = action.get("target", "")
        
        logger.info(f"Executing cleanup: {cleanup_type} on {target}")
        
        if cleanup_type == "organize_downloads":
            try:
                from app.agents.janitor.janitor_agent import organize_downloads
                result = await organize_downloads()
                logger.info(f"Downloads organized: {result}")
            except Exception as e:
                logger.error(f"Downloads organization failed: {e}")
    
    def _calculate_next_run(self, cron_config: Dict[str, Any], from_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time for cron task."""
        if from_time is None:
            from_time = datetime.now()
        
        # Start checking from the next minute
        next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Find next matching time (within 1 year limit)
        end_time = from_time + timedelta(days=366)
        
        while next_time < end_time:
            if CronParser.should_run(cron_config, next_time):
                return next_time
            next_time += timedelta(minutes=1)
        
        # Fallback to 1 day from now if no match found
        return from_time + timedelta(days=1)


# Global scheduler instance
_scheduler: Optional[SmartScheduler] = None

def get_scheduler() -> SmartScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SmartScheduler()
    return _scheduler


# Convenience decorator for scheduling functions
def scheduled(trigger_condition: str, trigger_type: TriggerType = TriggerType.CRON):
    """Decorator for scheduling functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Convert function to action plan
            action_plan = [{
                "action": "function_call",
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            }]
            
            scheduler = get_scheduler()
            task_id = scheduler.schedule(
                name=func.__name__,
                trigger_type=trigger_type,
                trigger_condition=trigger_condition,
                action_plan=action_plan
            )
            
            logger.info(f"Scheduled function {func.__name__} with trigger '{trigger_condition}'")
            return task_id
        
        return wrapper
    return decorator


# Predefined common schedules
def schedule_daily_cleanup():
    """Schedule daily cleanup at 2 AM."""
    scheduler = get_scheduler()
    return scheduler.schedule_cron(
        "0 2 * * *",
        "Daily Cleanup",
        [
            {
                "action": "agent_task",
                "agent": "JANITOR_AGENT",
                "intent": "clean and organize downloads and desktop"
            }
        ]
    )


def schedule_weekly_maintenance():
    """Schedule weekly maintenance on Sunday at midnight."""
    scheduler = get_scheduler()
    return scheduler.schedule_cron(
        "0 0 * * SUN",
        "Weekly Maintenance",
        [
            {
                "action": "agent_task",
                "agent": "JANITOR_AGENT", 
                "intent": "deep clean all directories and compress large files"
            },
            {
                "action": "cleanup",
                "type": "empty_recycle_bin"
            }
        ]
    )


def schedule_downloads_monitor():
    """Schedule monitoring of downloads folder."""
    scheduler = get_scheduler()
    return scheduler.schedule_file_event(
        "downloads > 50",
        "Downloads Overflow",
        [
            {
                "action": "agent_task",
                "agent": "JANITOR_AGENT",
                "intent": "organize downloads folder"
            }
        ]
    )


def schedule_battery_saver():
    """Schedule battery saving mode when battery is low."""
    scheduler = get_scheduler()
    return scheduler.schedule(
        "Battery Saver",
        TriggerType.BATTERY_EVENT,
        "battery < 20%",
        [
            {
                "action": "system_command",
                "command": "powercfg /setactive 961cc777-2547-4f9d-b4a6-2d480e1b38ed"  # Power saver mode
            }
        ]
    )