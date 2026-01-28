"""
Sentinel Daemon - Autonomous background monitoring service.

Continuously monitors system health and alerts user via WebSocket.
Features:
- 20-second monitoring intervals
- Persistent alerts with 2-minute cooldown
- Time-based thresholds (work hours vs night)
- Process reputation tracking
- 10-day resource history
- Multi-user support
- Windows Event Viewer integration
- Predictive analytics for resource exhaustion
- Anomaly detection
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import psutil
import platform

from fastapi.encoders import jsonable_encoder

from app.agents.sentinel.hardware_monitor import HardwareMonitor

logger = logging.getLogger(__name__)


@dataclass
class SentinelAlert:
    """Represents a system alert."""
    id: str
    type: str  # cpu, memory, temperature, disk, process, system_event, prediction, anomaly
    severity: str  # warning, critical
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    suggestions: List[str]
    processes: List[Dict[str, Any]]
    user_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


@dataclass
class SystemMetrics:
    """Current system metrics snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    temperature: Optional[float]
    disk_usage: Dict[str, float]
    network_io: Dict[str, float]
    processes: List[Dict[str, Any]]


class SentinelDaemon:
    """
    Autonomous system monitoring daemon.
    
    Monitors system health every 20 seconds and sends alerts via WebSocket.
    """
    
    def __init__(self):
        self.hardware_monitor = HardwareMonitor()
        self.running = False
        self.clients: Set[Any] = set()  # WebSocket clients
        
        # Configuration
        self.monitor_interval = 20  # seconds
        self.alert_cooldown = timedelta(minutes=2)
        self.history_days = 10
        
        # State tracking
        self.last_alerts: Dict[str, datetime] = {}  # cooldown tracking
        self.metrics_history = deque(maxlen=43200)  # 10 days @ 20s intervals
        self.process_reputation: Dict[str, Dict] = defaultdict(lambda: {
            "avg_cpu": 0, "avg_memory": 0, "samples": 0, "whitelisted": False
        })
        self.user_profiles: Dict[str, Dict] = defaultdict(lambda: {
            "work_hours": (9, 17), "gaming_mode": False, "notifications": True,
            "battery_aware": True, "on_battery": False, "battery_percent": 100
        })
        
        # Thresholds (adaptive based on time/context)
        self.base_thresholds = {
            "cpu": 90, "memory": 95, "temperature": 85, "disk": 90
        }
        
        # Active alerts
        self.active_alerts: Dict[str, SentinelAlert] = {}

        # Auto-remediation cooldowns (avoid repeatedly triggering heavy actions)
        self._remediation_last_run: Dict[str, datetime] = {}
        self._remediation_cooldown = timedelta(minutes=10)
        
        # Initialize advanced features
        self.event_monitor = None
        self.predictive_analyzer = None
        
        # Try to initialize Windows Event Monitor
        try:
            from app.agents.sentinel.event_monitor import WindowsEventMonitor
            self.event_monitor = WindowsEventMonitor(self)
        except ImportError:
            logger.info("[Sentinel] Windows Event Monitor not available")
        
        # Initialize Predictive Analyzer
        try:
            from app.agents.sentinel.predictive_analyzer import PredictiveAnalyzer
            self.predictive_analyzer = PredictiveAnalyzer(self)
        except ImportError:
            logger.info("[Sentinel] Predictive Analyzer not available")
        
        # Initialize Scheduled Maintenance
        try:
            from app.agents.sentinel.scheduled_maintenance import ScheduledMaintenance
            self.scheduled_maintenance = ScheduledMaintenance(self)
        except ImportError:
            logger.info("[Sentinel] Scheduled Maintenance not available")
        
        # Initialize Gaming Mode Detector
        try:
            from app.agents.sentinel.gaming_detector import GamingModeDetector
            self.gaming_detector = GamingModeDetector(self)
        except ImportError:
            logger.info("[Sentinel] Gaming Mode Detector not available")
        
    async def start(self):
        """Start the monitoring daemon."""
        logger.info("[Sentinel] Starting autonomous monitoring daemon...")
        self.running = True
        
        # Collect initial metrics immediately
        try:
            logger.info("[Sentinel] Collecting initial metrics...")
            initial_metrics = await self._collect_metrics()
            self.metrics_history.append(initial_metrics)
            
            # Feed initial data to predictive analyzer
            if self.predictive_analyzer:
                self.predictive_analyzer.add_metrics(initial_metrics)
                logger.info("[Sentinel] Initial metrics fed to predictive analyzer")
                
        except Exception as e:
            logger.error(f"[Sentinel] Failed to collect initial metrics: {e}")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
        # Start cleanup tasks
        asyncio.create_task(self._cleanup_loop())
        
        # Start advanced monitoring if available
        if self.event_monitor:
            asyncio.create_task(self._start_event_monitor())
        
        # Start scheduled maintenance if available
        if self.scheduled_maintenance:
            asyncio.create_task(self._start_scheduled_maintenance())
        
        # Start gaming mode detector if available
        if self.gaming_detector:
            asyncio.create_task(self._start_gaming_detector())
        
        logger.info("[Sentinel] Daemon started - monitoring every 20 seconds")
    
    async def _start_gaming_detector(self):
        """Start gaming mode detector."""
        try:
            await self.gaming_detector.start()
            logger.info("[Sentinel] Gaming Mode Detector started")
        except Exception as e:
            logger.error(f"[Sentinel] Failed to start Gaming Mode Detector: {e}")
    
    async def _start_scheduled_maintenance(self):
        """Start scheduled maintenance."""
        try:
            await self.scheduled_maintenance.start()
            logger.info("[Sentinel] Scheduled Maintenance started")
        except Exception as e:
            logger.error(f"[Sentinel] Failed to start Scheduled Maintenance: {e}")
    
    async def _start_event_monitor(self):
        """Start Windows Event Monitor."""
        try:
            await self.event_monitor.start()
            logger.info("[Sentinel] Windows Event Monitor started")
        except Exception as e:
            logger.error(f"[Sentinel] Failed to start Event Monitor: {e}")
    
    async def stop(self):
        """Stop the monitoring daemon."""
        logger.info("[Sentinel] Stopping daemon...")
        self.running = False
    
    async def register_client(self, websocket, user_id: str = None):
        """Register a WebSocket client for alerts."""
        self.clients.add(websocket)
        self.user_profiles[user_id]["websocket"] = websocket
        logger.info(f"[Sentinel] Client registered: {user_id or 'anonymous'}")
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client."""
        self.clients.discard(websocket)
        # Remove from user profiles
        for uid, profile in self.user_profiles.items():
            if profile.get("websocket") == websocket:
                profile["websocket"] = None
        logger.info("[Sentinel] Client disconnected")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs every 20 seconds."""
        while self.running:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Analyze for alerts
                alerts = await self._analyze_metrics(metrics)
                
                # Send alerts to clients
                for alert in alerts:
                    await self._send_alert(alert)
                
                # Update health score
                health_score = self._calculate_health_score(metrics)
                await self._broadcast_health_score(health_score)
                
                # Store metrics
                self.metrics_history.append(metrics)

                # Auto-remediation playbooks
                await self._run_remediation_playbooks(metrics)
                
                # Predictive analytics
                if self.predictive_analyzer:
                    self.predictive_analyzer.add_metrics(metrics)
                    
                    # Check predictions
                    predictions = self.predictive_analyzer.predict_resource_exhaustion()
                    for prediction in predictions:
                        await self._send_prediction_alert(prediction)
                    
                    # Check anomalies
                    anomalies = self.predictive_analyzer.detect_anomalies(metrics)
                    for anomaly in anomalies:
                        await self._send_anomaly_alert(anomaly)
                
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"[Sentinel] Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Quick retry on error

    def _is_gaming_mode(self) -> bool:
        try:
            return any(profile.get("gaming_mode") for profile in self.user_profiles.values())
        except Exception:
            return False

    def _remediation_ready(self, key: str, now: datetime) -> bool:
        last = self._remediation_last_run.get(key)
        if not last:
            return True
        return now - last > self._remediation_cooldown

    async def _run_remediation_playbooks(self, metrics: SystemMetrics) -> None:
        """Run safe automatic remediation when system is under pressure."""
        now = datetime.utcnow()

        # Do not auto-remediate while gaming.
        if self._is_gaming_mode():
            return

        # Disk pressure -> ask Janitor to generate aggressive reclaim plan.
        try:
            disk_pressure = any(usage >= 95 for usage in metrics.disk_usage.values())
        except Exception:
            disk_pressure = False

        if disk_pressure and self._remediation_ready("disk_pressure", now):
            self._remediation_last_run["disk_pressure"] = now
            await self._trigger_cleanup(mode="disk_pressure")

        # Memory pressure -> trigger temp/cache cleanup plan.
        if metrics.memory_percent >= 95 and self._remediation_ready("memory_pressure", now):
            self._remediation_last_run["memory_pressure"] = now
            await self._trigger_cleanup(mode="memory_pressure")
    
    async def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        # Get hardware report
        health_report = await self.hardware_monitor.get_health_report()
        
        # Extract metrics
        cpu_info = health_report.get("cpu", {})
        memory_info = health_report.get("memory", {})
        temp_info = health_report.get("temperature", {})
        disk_info = health_report.get("disk", {})
        network_info = health_report.get("network", {})
        
        # Get top processes
        processes = await self.hardware_monitor._get_process_info(limit=10)
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_info.get("percent_total", 0),
            memory_percent=memory_info.get("virtual", {}).get("percent_used", 0),
            temperature=temp_info.get("max_temp"),
            disk_usage={drive: info.get("percent_used", 0) 
                       for drive, info in disk_info.get("usage", {}).items()},
            network_io={
                "bytes_sent_per_sec": network_info.get("bytes_sent_per_sec", 0),
                "bytes_recv_per_sec": network_info.get("bytes_recv_per_sec", 0)
            },
            processes=processes
        )
    
    async def _analyze_metrics(self, metrics: SystemMetrics) -> List[SentinelAlert]:
        """Analyze metrics and generate alerts."""
        alerts = []
        current_time = datetime.utcnow()
        
        # Get adaptive thresholds based on time and context
        thresholds = self._get_adaptive_thresholds()
        
        # CPU monitoring
        if metrics.cpu_percent > thresholds["cpu"]:
            if self._should_alert("cpu", current_time):
                alert = await self._create_cpu_alert(metrics, thresholds["cpu"])
                alerts.append(alert)
        
        # Memory monitoring
        if metrics.memory_percent > thresholds["memory"]:
            if self._should_alert("memory", current_time):
                alert = await self._create_memory_alert(metrics, thresholds["memory"])
                alerts.append(alert)
        
        # Temperature monitoring
        if metrics.temperature and metrics.temperature > thresholds["temperature"]:
            if self._should_alert("temperature", current_time):
                alert = await self._create_temperature_alert(metrics, thresholds["temperature"])
                alerts.append(alert)
        
        # Disk monitoring
        for drive, usage in metrics.disk_usage.items():
            if usage > thresholds["disk"]:
                if self._should_alert(f"disk_{drive}", current_time):
                    alert = await self._create_disk_alert(metrics, drive, usage, thresholds["disk"])
                    alerts.append(alert)
        
        # Process monitoring (new high-usage processes)
        process_alerts = await self._analyze_processes(metrics)
        alerts.extend(process_alerts)
        
        return alerts
    
    def _get_adaptive_thresholds(self) -> Dict[str, float]:
        """Get adaptive thresholds based on time and context."""
        thresholds = self.base_thresholds.copy()
        current_hour = datetime.now().hour
        
        # Time-based adjustments
        for user_id, profile in self.user_profiles.items():
            work_start, work_end = profile["work_hours"]
            
            # Night mode - more lenient thresholds
            if current_hour < work_start or current_hour > work_end:
                thresholds["cpu"] *= 1.1  # 10% more lenient
                thresholds["memory"] *= 1.05
            
            # Gaming mode - suppress non-critical alerts
            if profile.get("gaming_mode"):
                thresholds["cpu"] *= 1.2  # 20% more lenient
                thresholds["memory"] *= 1.1
            
            # Battery awareness - more lenient on battery to save power
            if profile.get("battery_aware") and profile.get("on_battery"):
                battery_percent = profile.get("battery_percent", 100)
                
                # Very aggressive power saving when battery is low
                if battery_percent < 20:
                    thresholds["cpu"] *= 1.3  # 30% more lenient
                    thresholds["memory"] *= 1.15
                elif battery_percent < 50:
                    thresholds["cpu"] *= 1.2  # 20% more lenient
                    thresholds["memory"] *= 1.1
                else:
                    thresholds["cpu"] *= 1.1  # 10% more lenient
                    thresholds["memory"] *= 1.05
        
        return thresholds
    
    def _should_alert(self, alert_type: str, current_time: datetime) -> bool:
        """Check if we should send an alert (cooldown check)."""
        last_alert = self.last_alerts.get(alert_type)
        if not last_alert:
            return True
        
        return current_time - last_alert > self.alert_cooldown
    
    async def _create_cpu_alert(self, metrics: SystemMetrics, threshold: float) -> SentinelAlert:
        """Create CPU usage alert."""
        # Find top CPU processes
        top_processes = [p for p in metrics.processes if p["cpu_percent"] > 10][:5]
        
        alert = SentinelAlert(
            id=f"cpu_{int(metrics.timestamp.timestamp())}",
            type="cpu",
            severity="critical" if metrics.cpu_percent > 95 else "warning",
            message=f"CPU usage at {metrics.cpu_percent:.1f}%",
            current_value=metrics.cpu_percent,
            threshold=threshold,
            timestamp=metrics.timestamp,
            suggestions=["kill_processes", "adjust_priority", "ignore"],
            processes=top_processes
        )
        
        self.last_alerts["cpu"] = metrics.timestamp
        self.active_alerts[alert.id] = alert
        return alert
    
    async def _create_memory_alert(self, metrics: SystemMetrics, threshold: float) -> SentinelAlert:
        """Create memory usage alert."""
        top_processes = sorted(metrics.processes, 
                              key=lambda x: x["memory_mb"], reverse=True)[:5]
        
        alert = SentinelAlert(
            id=f"memory_{int(metrics.timestamp.timestamp())}",
            type="memory",
            severity="critical" if metrics.memory_percent > 98 else "warning",
            message=f"Memory usage at {metrics.memory_percent:.1f}%",
            current_value=metrics.memory_percent,
            threshold=threshold,
            timestamp=metrics.timestamp,
            suggestions=["close_apps", "clear_cache", "restart_apps"],
            processes=top_processes
        )
        
        self.last_alerts["memory"] = metrics.timestamp
        self.active_alerts[alert.id] = alert
        return alert
    
    async def _create_temperature_alert(self, metrics: SystemMetrics, threshold: float) -> SentinelAlert:
        """Create temperature alert."""
        alert = SentinelAlert(
            id=f"temp_{int(metrics.timestamp.timestamp())}",
            type="temperature",
            severity="critical" if metrics.temperature > 90 else "warning",
            message=f"Temperature at {metrics.temperature}°C",
            current_value=metrics.temperature,
            threshold=threshold,
            timestamp=metrics.timestamp,
            suggestions=["thermal_management", "reduce_load", "check_cooling"],
            processes=[]
        )
        
        self.last_alerts["temperature"] = metrics.timestamp
        self.active_alerts[alert.id] = alert
        return alert
    
    async def _create_disk_alert(self, metrics: SystemMetrics, drive: str, 
                               usage: float, threshold: float) -> SentinelAlert:
        """Create disk usage alert."""
        alert = SentinelAlert(
            id=f"disk_{drive}_{int(metrics.timestamp.timestamp())}",
            type="disk",
            severity="critical" if usage > 95 else "warning",
            message=f"Drive {drive.upper()} at {usage:.1f}% capacity",
            current_value=usage,
            threshold=threshold,
            timestamp=metrics.timestamp,
            suggestions=["cleanup", "archive_files", "disk_cleanup"],
            processes=[]
        )
        
        self.last_alerts[f"disk_{drive}"] = metrics.timestamp
        self.active_alerts[alert.id] = alert
        return alert
    
    async def _analyze_processes(self, metrics: SystemMetrics) -> List[SentinelAlert]:
        """Analyze processes for new high-usage applications."""
        alerts = []
        current_time = metrics.timestamp
        
        for process in metrics.processes:
            if process["cpu_percent"] > 50 or process["memory_mb"] > 1000:
                proc_name = process["name"]
                
                # Update process reputation
                self._update_process_reputation(proc_name, process)
                
                # Check if this is unusually high for this process
                reputation = self.process_reputation[proc_name]
                if (process["cpu_percent"] > reputation["avg_cpu"] * 2 and 
                    not reputation["whitelisted"] and
                    self._should_alert(f"process_{proc_name}", current_time)):
                    
                    alert = SentinelAlert(
                        id=f"process_{proc_name}_{int(current_time.timestamp())}",
                        type="process",
                        severity="warning",
                        message=f"High resource usage from {proc_name}",
                        current_value=process["cpu_percent"],
                        threshold=reputation["avg_cpu"] * 2,
                        timestamp=current_time,
                        suggestions=["limit_priority", "terminate", "whitelist"],
                        processes=[process]
                    )
                    
                    alerts.append(alert)
                    self.last_alerts[f"process_{proc_name}"] = current_time
                    self.active_alerts[alert.id] = alert
        
        return alerts
    
    def _update_process_reputation(self, proc_name: str, process: Dict):
        """Update process reputation tracking."""
        reputation = self.process_reputation[proc_name]
        
        # Update running averages
        reputation["avg_cpu"] = (
            (reputation["avg_cpu"] * reputation["samples"] + process["cpu_percent"]) /
            (reputation["samples"] + 1)
        )
        reputation["avg_memory"] = (
            (reputation["avg_memory"] * reputation["samples"] + process["memory_mb"]) /
            (reputation["samples"] + 1)
        )
        reputation["samples"] += 1
    
    def _calculate_health_score(self, metrics: SystemMetrics) -> int:
        """Calculate overall system health score (0-100)."""
        score = 100
        
        # CPU impact
        if metrics.cpu_percent > 90:
            score -= 20
        elif metrics.cpu_percent > 70:
            score -= 10
        
        # Memory impact
        if metrics.memory_percent > 95:
            score -= 20
        elif metrics.memory_percent > 80:
            score -= 10
        
        # Temperature impact
        if metrics.temperature and metrics.temperature > 85:
            score -= 15
        elif metrics.temperature and metrics.temperature > 70:
            score -= 5
        
        # Disk impact
        for usage in metrics.disk_usage.values():
            if usage > 95:
                score -= 15
            elif usage > 90:
                score -= 5
        
        return max(0, score)
    
    async def _send_alert(self, alert: SentinelAlert):
        """Send alert to all connected clients."""
        message = {
            "type": "sentinel_alert",
            **asdict(alert),
            "timestamp": alert.timestamp.isoformat()
        }
        
        await self._broadcast_message(message)
        logger.info(f"[Sentinel] Alert sent: {alert.type} - {alert.message}")
    
    async def _send_prediction_alert(self, prediction: Dict):
        """Send predictive alert."""
        alert_id = f"prediction_{prediction['type']}_{int(datetime.utcnow().timestamp())}"
        
        alert = SentinelAlert(
            id=alert_id,
            type="prediction",
            severity=prediction.get("severity", "warning"),
            message=f"Prediction: {prediction['type'].replace('_', ' ').title()} in {prediction.get('time_to_exhaustion', 0)}s",
            current_value=prediction.get("current_value", 0),
            threshold=prediction.get("predicted_value", 0),
            timestamp=datetime.utcnow(),
            suggestions=["prepare", "investigate", "ignore"],
            processes=[],
            extra_data=prediction
        )
        
        self.active_alerts[alert_id] = alert
        await self._send_alert(alert)
    
    async def _send_anomaly_alert(self, anomaly: Dict):
        """Send anomaly alert."""
        alert_id = f"anomaly_{anomaly['type']}_{int(datetime.utcnow().timestamp())}"
        
        alert = SentinelAlert(
            id=alert_id,
            type="anomaly",
            severity=anomaly.get("severity", "warning"),
            message=f"Anomaly detected: {anomaly['type'].replace('_', ' ').title()}",
            current_value=anomaly.get("current_value", 0),
            threshold=anomaly.get("normal_mean", 0),
            timestamp=datetime.utcnow(),
            suggestions=["investigate", "monitor", "ignore"],
            processes=[],
            extra_data=anomaly
        )
        
        self.active_alerts[alert_id] = alert
        await self._send_alert(alert)
    
    async def _broadcast_health_score(self, score: int):
        """Broadcast system health score."""
        message = {
            "type": "sentinel_health_score",
            "score": score,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        message_str = json.dumps(jsonable_encoder(message))
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send_text(message_str)
            except Exception as e:
                logger.warning(f"[Sentinel] Failed to send to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            await self.unregister_client(client)
    
    async def _cleanup_loop(self):
        """Periodic cleanup of old data."""
        while self.running:
            try:
                # Clean old alerts (older than 1 hour)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                old_alerts = [aid for aid, alert in self.active_alerts.items() 
                            if alert.timestamp < cutoff_time]
                
                for aid in old_alerts:
                    del self.active_alerts[aid]
                
                # Clean old cooldown entries
                old_cooldowns = [atype for atype, last_time in self.last_alerts.items() 
                               if last_time < cutoff_time]
                
                for atype in old_cooldowns:
                    del self.last_alerts[atype]
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"[Sentinel] Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def handle_user_response(self, response: Dict):
        """Handle user action response."""
        alert_id = response.get("alert_id")
        action = response.get("action")
        approved = response.get("approved", False)
        
        if not approved:
            logger.info(f"[Sentinel] User declined action for alert {alert_id}")
            return
        
        # Execute action based on response
        if action == "kill_processes":
            await self._kill_processes(response.get("targets", []))
        elif action == "adjust_priority":
            await self._adjust_process_priority(response.get("targets", []))
        elif action == "cleanup":
            await self._trigger_cleanup()
        elif action == "whitelist":
            await self._whitelist_process(response.get("process_name"))
        
        logger.info(f"[Sentinel] Executed action: {action} for alert {alert_id}")
    
    async def handle_message(self, websocket, user_id: str, message: Dict):
        """Handle incoming message from client."""
        message_type = message.get("type")
        
        if message_type == "sentinel_action":
            # User responded to an alert
            await self.handle_user_response({
                **message,
                "user_id": user_id
            })
        
        elif message_type == "update_profile":
            # Update user preferences
            profile = message.get("profile", {})
            self.user_profiles[user_id].update(profile)
            logger.info(f"[Sentinel] Updated profile for {user_id}: {profile}")
        
        elif message_type == "whitelist_process":
            # Whitelist a process
            process_name = message.get("process_name")
            await self._whitelist_process(process_name)
        
        elif message_type == "battery_status":
            # Update battery status
            self.user_profiles[user_id]["on_battery"] = message.get("on_battery", False)
            self.user_profiles[user_id]["battery_percent"] = message.get("battery_percent", 100)
            logger.info(f"[Sentinel] Battery status updated: on_battery={message.get('on_battery')}, percent={message.get('battery_percent')}")
        
        else:
            logger.warning(f"[Sentinel] Unknown message type: {message_type}")
    
    async def _kill_processes(self, pids: List[int]):
        """Kill specified processes."""
        for pid in pids:
            try:
                psutil.Process(pid).terminate()
                logger.info(f"[Sentinel] Terminated process {pid}")
            except Exception as e:
                logger.error(f"[Sentinel] Failed to kill process {pid}: {e}")
    
    async def _adjust_process_priority(self, pids: List[int]):
        """Adjust process priority to low."""
        for pid in pids:
            try:
                process = psutil.Process(pid)
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if platform.system() == "Windows" else 10)
                logger.info(f"[Sentinel] Adjusted priority for process {pid}")
            except Exception as e:
                logger.error(f"[Sentinel] Failed to adjust priority for {pid}: {e}")
    
    async def _trigger_cleanup(self, mode: str = "cleanup"):
        """Trigger system cleanup via Janitor agent."""
        try:
            # Import Janitor to trigger cleanup
            from app.agents.janitor.janitor_agent import JanitorAgent
            from app.agents.agent_registry import get_registry
            
            registry = get_registry()
            janitor = registry.get("JANITOR_AGENT")
            
            if janitor:
                # Create cleanup context
                context = {
                    "intent": "cleanup",
                    "mode": mode,
                    "user_request": f"System cleanup triggered by Sentinel ({mode})",
                    "autonomous": True
                }
                
                # Run Janitor analysis and planning
                analysis = await janitor.analyze(context)
                plan = await janitor.plan(analysis)
                
                # Execute cleanup actions (with approval already given)
                if plan.actions:
                    plan.approve()
                    result = await janitor.execute(plan)
 
                    await self._broadcast_message({
                        "type": "sentinel_cleanup_completed",
                        "actions_executed": len(plan.actions),
                        "result": result.model_dump() if hasattr(result, "model_dump") else result,
                        "message": f"Cleanup completed: {len(plan.actions)} actions taken"
                    })
                 
                logger.info(f"[Sentinel] Triggered Janitor cleanup: {len(plan.actions)} actions")
            else:
                logger.warning("[Sentinel] Janitor agent not available for cleanup")
        
        except Exception as e:
            logger.error(f"[Sentinel] Failed to trigger cleanup: {e}")
            await self._broadcast_message({
                "type": "sentinel_cleanup_failed",
                "error": str(e)
            })
    
    async def _whitelist_process(self, process_name: str):
        """Add process to whitelist."""
        self.process_reputation[process_name]["whitelisted"] = True
        logger.info(f"[Sentinel] Whitelisted process: {process_name}")
    
    def get_status(self) -> Dict:
        """Get daemon status."""
        return {
            "running": self.running,
            "clients": len(self.clients),
            "active_alerts": len(self.active_alerts),
            "metrics_history": len(self.metrics_history),
            "process_reputation": len(self.process_reputation),
            "last_check": datetime.utcnow().isoformat()
        }


# Global daemon instance
_sentinel_daemon = None

def get_sentinel_daemon() -> SentinelDaemon:
    """Get the global Sentinel daemon instance."""
    global _sentinel_daemon
    if _sentinel_daemon is None:
        _sentinel_daemon = SentinelDaemon()
    return _sentinel_daemon
