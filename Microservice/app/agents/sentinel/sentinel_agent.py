"""
Sentinel Agent - Hardware & Performance monitoring specialist.

The Sentinel Agent ensures PC responsiveness by monitoring:
- CPU spikes and resource hogs
- RAM leaks and memory pressure  
- Thermal states (CPU/GPU temperatures)
- Process priorities and power profiles
- Ghost processes and system lag

This is a HYBRID agent:
- CONTINUOUS: Runs in background monitoring system health
- ON_DEMAND: Can be triggered by user ("optimize performance")

Success Metrics:
- System responsiveness improvement
- Temperature reduction under load
- Resource recovery from terminated processes
- Power profile optimization
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentTrigger,
    AnalysisResult,
    ActionPlan,
    ExecutionResult,
)
from .hardware_monitor import HardwareMonitor
from .process_optimizer import ProcessOptimizer
from .thermal_controller import ThermalController

logger = logging.getLogger(__name__)


class SentinelAgent(BaseAgent):
    """
    Sentinel Agent - The "Nervous System" for PC performance.
    
    Monitors hardware health, manages thermal states, and optimizes system performance
    by managing process priorities and resource leaks.
    """
    
    name = "SENTINEL_AGENT"
    specialization = "Hardware monitoring, thermal management, and system performance optimization"
    agent_type = AgentType.HYBRID  # Both continuous and on-demand
    
    # Trigger thresholds
    CPU_THRESHOLD = 90.0      # CPU usage percentage
    TEMP_THRESHOLD = 85.0    # Temperature in Celsius
    RAM_THRESHOLD = 95.0    # RAM usage percentage
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self._hardware_monitor = HardwareMonitor()
        self._process_optimizer = ProcessOptimizer()
        self._thermal_controller = ThermalController()
        
        # Performance metrics
        self._metrics = {
            "health_checks": 0,
            "optimizations_performed": 0,
            "processes_terminated": 0,
            "temperature_alerts": 0,
            "power_profile_changes": 0,
            "ghost_processes_cleaned": 0,
        }
        
        # Last health report for continuous monitoring
        self._last_health_report = None
        self._last_optimization = None
        
        logger.info("[Sentinel] Hardware & Performance agent initialized")
    
    def get_triggers(self) -> List[AgentTrigger]:
        """Define what triggers this agent."""
        return [
            # System pulse triggers (for Control Tower)
            AgentTrigger(
                trigger_type="system_pulse",
                condition=f"cpu_usage > {self.CPU_THRESHOLD}%",
                priority=8
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition=f"temperature > {self.TEMP_THRESHOLD}°C",
                priority=9
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition=f"ram_usage > {self.RAM_THRESHOLD}%",
                priority=7
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition="system_lag_detected",
                priority=8
            ),
            
            # User intent triggers (for LLM Planner)
            AgentTrigger(
                trigger_type="user_intent",
                condition="optimize performance lag slow cpu memory temperature",
                priority=9
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="kill process terminate hog resource",
                priority=8
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="focus mode optimize for app game",
                priority=9
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="thermal temperature fan cooling",
                priority=7
            ),
        ]
    
    async def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        """
        Comprehensive system health analysis.
        
        Analyzes:
        - Hardware telemetry (CPU, RAM, temperature, disk, network)
        - Process resource usage
        - Thermal state
        - System alerts
        
        Returns detailed findings and optimization recommendations.
        """
        logger.info("[Sentinel] Starting system health analysis...")
        self._status.current_task = "Analyzing system health and performance"
        
        findings = {}
        recommendations = []
        severity = "info"
        
        try:
            # Get comprehensive health report
            health_report = await self._hardware_monitor.get_health_report()
            self._last_health_report = health_report
            self._metrics["health_checks"] += 1
            
            findings["health_report"] = health_report
            
            # Analyze CPU usage
            cpu_info = health_report.get("cpu", {})
            cpu_percent = cpu_info.get("percent_total", 0)
            
            if cpu_percent > self.CPU_THRESHOLD:
                severity = "critical" if cpu_percent > 95 else "warning"
                recommendations.append(f"High CPU usage detected ({cpu_percent}%) - consider terminating resource hogs")
            
            # Analyze memory usage
            memory_info = health_report.get("memory", {}).get("virtual", {})
            memory_percent = memory_info.get("percent_used", 0)
            
            if memory_percent > self.RAM_THRESHOLD:
                severity = "critical" if memory_percent > 98 else "warning"
                recommendations.append(f"High memory usage detected ({memory_percent}%) - cleanup recommended")
            
            # Analyze temperature
            temp_info = health_report.get("temperature", {})
            max_temp = temp_info.get("max_temp", 0)
            
            # Ensure max_temp is numeric before comparison
            if isinstance(max_temp, (int, float)) and max_temp > self.TEMP_THRESHOLD:
                severity = "critical" if isinstance(max_temp, (int, float)) and max_temp > 90 else "warning"
                recommendations.append(f"High temperature detected ({max_temp}°C) - thermal management needed")
                self._metrics["temperature_alerts"] += 1
            
            # Identify resource hogs
            processes = health_report.get("processes", [])
            resource_hogs = await self._process_optimizer._identify_background_hogs(0, cpu_threshold=10.0)
            
            if resource_hogs:
                findings["resource_hogs"] = resource_hogs
                hog_count = len(resource_hogs)
                recommendations.append(f"Found {hog_count} resource hog processes consuming excessive CPU/memory")
            
            # Identify heat sources if temperature is high
            if isinstance(max_temp, (int, float)) and max_temp > 75:
                heat_sources = await self._thermal_controller.identify_heat_sources(processes)
                if heat_sources:
                    findings["heat_sources"] = heat_sources
                    recommendations.append(f"Identified {len(heat_sources)} potential heat sources")
            
            # Check for ghost processes
            ghost_candidates = [p for p in processes if p.get("cpu_percent", 0) < 0.1 and p.get("memory_percent", 0) > 1]
            if len(ghost_candidates) > 5:
                findings["ghost_candidates"] = ghost_candidates[:10]
                recommendations.append(f"Found {len(ghost_candidates)} potentially idle processes")
            
            # System overview
            findings["system_status"] = {
                "cpu_status": "critical" if cpu_percent > 95 else "warning" if cpu_percent > 80 else "normal",
                "memory_status": "critical" if memory_percent > 95 else "warning" if memory_percent > 85 else "normal",
                "thermal_status": "critical" if isinstance(max_temp, (int, float)) and max_temp > 90 else "warning" if isinstance(max_temp, (int, float)) and max_temp > 80 else "normal",
                "overall_status": severity,
            }
            
            logger.info(f"[Sentinel] Analysis complete: CPU={cpu_percent}%, RAM={memory_percent}%, Temp={max_temp}°C")
            
        except Exception as e:
            logger.error(f"[Sentinel] Analysis failed: {e}")
            severity = "critical"
            recommendations.append(f"Analysis error: {str(e)}")
        
        return AnalysisResult(
            agent_name=self.name,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
        )
    
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """
        Create optimization plan based on analysis.
        
        Plans may include:
        - Process priority adjustments
        - Resource hog termination
        - Power profile changes
        - Ghost process cleanup
        - Thermal management actions
        """
        logger.info("[Sentinel] Creating optimization plan...")
        self._status.current_task = "Creating performance optimization plan"
        
        plan = ActionPlan(
            agent_name=self.name,
            analysis_id=analysis.analysis_id,
            requires_approval=True,  # Safety first for system changes
        )
        
        findings = analysis.findings
        actions = []
        
        try:
            health_report = findings.get("health_report", {})
            system_status = findings.get("system_status", {})
            
            # CPU optimization actions
            if system_status.get("cpu_status") == "critical":
                resource_hogs = findings.get("resource_hogs", [])
                for hog in resource_hogs[:3]:  # Limit to top 3
                    actions.append({
                        "type": "terminate_process",
                        "target": hog["name"],
                        "pid": hog["pid"],
                        "reason": f"Excessive CPU usage: {hog['cpu_percent']}%",
                        "priority": "high",
                    })
            
            # Memory optimization actions
            if system_status.get("memory_status") == "critical":
                ghost_candidates = findings.get("ghost_candidates", [])
                for ghost in ghost_candidates[:5]:  # Limit to top 5
                    actions.append({
                        "type": "cleanup_ghost",
                        "target": ghost["name"],
                        "pid": ghost["pid"],
                        "reason": f"Idle process consuming {ghost['memory_percent']}% RAM",
                        "priority": "medium",
                    })
            
            # Thermal management actions
            if system_status.get("thermal_status") in ["critical", "warning"]:
                max_temp = health_report.get("temperature", {}).get("max_temp", 0)
                
                if isinstance(max_temp, (int, float)) and max_temp > 90:
                    actions.append({
                        "type": "thermal_emergency",
                        "action": "power_saver",
                        "reason": f"Emergency temperature: {max_temp}°C",
                        "priority": "critical",
                    })
                elif max_temp > 85:
                    actions.append({
                        "type": "thermal_management",
                        "action": "balanced_power",
                        "reason": f"High temperature: {max_temp}°C",
                        "priority": "high",
                    })
            
            # Heat source throttling
            heat_sources = findings.get("heat_sources", [])
            for source in heat_sources[:2]:  # Limit to top 2 heat sources
                actions.append({
                    "type": "throttle_process",
                    "target": source["name"],
                    "pid": source["pid"],
                    "reason": f"Heat source with score: {source['heat_score']}",
                    "priority": "medium",
                })
            
            plan.actions = actions
            plan.estimated_impact = f"System optimization with {len(actions)} actions"
            
            logger.info(f"[Sentinel] Plan created: {len(actions)} optimization actions")
            
        except Exception as e:
            logger.error(f"[Sentinel] Plan creation failed: {e}")
            plan.actions = [{
                "type": "error",
                "reason": f"Plan creation failed: {str(e)}",
                "priority": "low",
            }]
        
        return plan
    
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """
        Execute approved optimization plan.
        
        Executes:
        - Process terminations
        - Priority adjustments
        - Power profile changes
        - Ghost process cleanup
        - Thermal management
        """
        if not plan.approved:
            return ExecutionResult(
                plan_id=plan.plan_id,
                agent_name=self.name,
                status="failed",
                errors=["Plan not approved"]
            )
        
        logger.info(f"[Sentinel] Executing optimization plan {plan.plan_id}...")
        self._status.current_task = "Executing performance optimizations"
        
        completed = 0
        failed = 0
        errors = []
        metrics = {}
        
        try:
            for action in plan.actions:
                action_type = action.get("type")
                success = False
                
                if action_type == "terminate_process":
                    success = await self._execute_terminate_action(action)
                    if success:
                        self._metrics["processes_terminated"] += 1
                
                elif action_type == "cleanup_ghost":
                    success = await self._execute_ghost_cleanup(action)
                    if success:
                        self._metrics["ghost_processes_cleaned"] += 1
                
                elif action_type == "throttle_process":
                    success = await self._execute_throttle_action(action)
                
                elif action_type in ["thermal_emergency", "thermal_management"]:
                    success = await self._execute_thermal_action(action)
                    if success:
                        self._metrics["power_profile_changes"] += 1
                
                else:
                    logger.warning(f"[Sentinel] Unknown action type: {action_type}")
                    success = False
                
                if success:
                    completed += 1
                else:
                    failed += 1
                    errors.append(f"Failed action: {action_type}")
            
            # Update metrics
            self._metrics["optimizations_performed"] += completed
            
            status = "success" if failed == 0 else "partial" if completed > 0 else "failed"
            
            logger.info(f"[Sentinel] Execution complete: {completed} done, {failed} failed")
            
            return ExecutionResult(
                plan_id=plan.plan_id,
                agent_name=self.name,
                status=status,
                actions_completed=completed,
                actions_failed=failed,
                metrics=self._metrics.copy(),
                errors=errors,
            )
        
        except Exception as e:
            logger.error(f"[Sentinel] Execution failed: {e}")
            return ExecutionResult(
                plan_id=plan.plan_id,
                agent_name=self.name,
                status="failed",
                actions_completed=completed,
                actions_failed=failed,
                errors=[str(e)],
            )
    
    async def _execute_terminate_action(self, action: Dict[str, Any]) -> bool:
        """Execute process termination action."""
        try:
            pid = action.get("pid")
            name = action.get("target")
            
            result = await self._process_optimizer._terminate_process(pid, name)
            return result.get("success", False)
        
        except Exception as e:
            logger.error(f"[Sentinel] Terminate action failed: {e}")
            return False
    
    async def _execute_ghost_cleanup(self, action: Dict[str, Any]) -> bool:
        """Execute ghost process cleanup action."""
        try:
            pid = action.get("pid")
            name = action.get("target")
            
            result = await self._process_optimizer._terminate_process(pid, name)
            return result.get("success", False)
        
        except Exception as e:
            logger.error(f"[Sentinel] Ghost cleanup failed: {e}")
            return False
    
    async def _execute_throttle_action(self, action: Dict[str, Any]) -> bool:
        """Execute process throttling action."""
        try:
            pid = action.get("pid")
            
            # Set to low priority
            result = await self._process_optimizer._set_process_priority(pid, "below_normal")
            return result.get("success", False)
        
        except Exception as e:
            logger.error(f"[Sentinel] Throttle action failed: {e}")
            return False
    
    async def _execute_thermal_action(self, action: Dict[str, Any]) -> bool:
        """Execute thermal management action."""
        try:
            thermal_action = action.get("action")
            
            if thermal_action == "power_saver":
                result = await self._thermal_controller.set_power_profile("power_saver")
            elif thermal_action == "balanced_power":
                result = await self._thermal_controller.set_power_profile("balanced")
            else:
                result = {"success": False, "reason": f"Unknown thermal action: {thermal_action}"}
            
            return result.get("success", False)
        
        except Exception as e:
            logger.error(f"[Sentinel] Thermal action failed: {e}")
            return False
    
    # Public API methods for direct access
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get current system health report."""
        return await self._hardware_monitor.get_health_report()
    
    async def optimize_for_focus(self, target_app: str) -> Dict[str, Any]:
        """Optimize system for specific target application."""
        result = await self._process_optimizer.optimize_for_focus(target_app)
        self._last_optimization = result
        return result
    
    async def kill_resource_hogs(self, cpu_threshold: float = 90.0, memory_threshold: float = 95.0) -> Dict[str, Any]:
        """Kill resource hog processes."""
        return await self._process_optimizer.kill_resource_hogs(cpu_threshold, memory_threshold)
    
    async def cleanup_ghost_processes(self, idle_hours: float = 2.0) -> Dict[str, Any]:
        """Clean up ghost processes."""
        return await self._process_optimizer.cleanup_ghost_processes(idle_hours)
    
    async def set_power_profile(self, profile: str) -> Dict[str, Any]:
        """Set Windows power profile."""
        return await self._thermal_controller.set_power_profile(profile)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._metrics.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        base_status = self.status.model_dump()
        
        return {
            **base_status,
            "metrics": self._metrics,
            "thermal_status": self._thermal_controller.get_current_status(),
            "last_health_check": self._last_health_report.get("timestamp") if self._last_health_report else None,
            "last_optimization": self._last_optimization.get("timestamp") if self._last_optimization else None,
        }
