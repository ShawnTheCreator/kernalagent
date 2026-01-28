"""
Windows Event Viewer integration for Sentinel.

Monitors Windows Event Logs for system events and integrates with Sentinel alerts.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import platform

logger = logging.getLogger(__name__)

try:
    import win32evtlog
    import win32con
    import win32evtlogutil
    EVENT_LOG_AVAILABLE = True
except ImportError:
    EVENT_LOG_AVAILABLE = False
    logger.warning("Windows Event Log integration not available - pywin32 not installed")


class WindowsEventMonitor:
    """Monitors Windows Event Viewer for system events."""
    
    def __init__(self, sentinel_daemon):
        self.daemon = sentinel_daemon
        self.running = False
        self.event_handlers = {
            "System": self._handle_system_event,
            "Application": self._handle_application_event,
            "Security": self._handle_security_event,
        }
        
        # Critical event IDs to monitor
        self.critical_events = {
            'System': {
                41: "Critical system reboot (bugcheck)",
                1074: "System shutdown/restart",
                6008: "Unexpected shutdown",
                7036: "Service state change",
                7040: "Service start failed",
                7031: "Service crashed",
                7034: "Service terminated unexpectedly",
                7023: "Service hung on start",
                7024: "Service hung on stop",
                55: "File system corruption",
                57: "NTFS file system error",
                50: "Delayed write failed",
            },
            'Application': {
                1000: "Application crash",
                1001: "Application fault bucket",
                1002: "Application hang",
                1003: "Application error",
                1024: "Application configuration error",
            }
        }
    
    async def start(self):
        """Start monitoring Windows Event Logs."""
        if not EVENT_LOG_AVAILABLE or platform.system() != "Windows":
            logger.info("[Sentinel] Event Log monitoring not available on this platform")
            return
        
        self.running = True
        logger.info("[Sentinel] Starting Windows Event Log monitoring...")
        
        # Start monitoring loop
        asyncio.create_task(self._event_monitoring_loop())
    
    async def stop(self):
        """Stop monitoring."""
        self.running = False
    
    async def _event_monitoring_loop(self):
        """Main event monitoring loop."""
        while self.running:
            try:
                # Check each event log
                for log_type, handler in self.event_handlers.items():
                    await self._check_event_log(log_type, handler)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"[Sentinel] Event monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_event_log(self, log_type, handler):
        """Check a specific event log for new events."""
        try:
            # Open event log
            server = None  # Local computer
            log_handle = win32evtlog.OpenEventLog(server, log_type)
            
            # Get the number of records
            total_records = win32evtlog.GetNumberOfEventLogRecords(log_handle)
            
            # Read the last 10 records (most recent)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(log_handle, flags, 0)
            
            # Process events from last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            for event in events:
                event_time = event.TimeGenerated
                if event_time >= cutoff_time:
                    await handler(event)
            
            win32evtlog.CloseEventLog(log_handle)
            
        except Exception as e:
            logger.debug(f"[Sentinel] Failed to check {log_type} log: {e}")
    
    async def _handle_system_event(self, event):
        """Handle system event log entries."""
        event_id = event.EventID
        source = event.SourceName
        
        # Check if this is a critical event
        if event_id in self.critical_events.get('System', {}):
            description = self.critical_events['System'][event_id]
            
            # Create alert
            alert_id = f"event_system_{event_id}_{int(event.TimeGenerated.timestamp())}"
            
            from app.agents.sentinel.sentinel_daemon import SentinelAlert
            
            alert = SentinelAlert(
                id=alert_id,
                type="system_event",
                severity="critical" if event_id in [41, 6008] else "warning",
                message=f"System Event: {description}",
                current_value=event_id,
                threshold=0,
                timestamp=event.TimeGenerated,
                suggestions=["investigate", "check_logs", "ignore"],
                processes=[],
                user_id=None
            )
            
            # Check cooldown
            if self.daemon._should_alert(f"event_system_{event_id}", datetime.utcnow()):
                self.daemon.last_alerts[f"event_system_{event_id}"] = datetime.utcnow()
                self.daemon.active_alerts[alert_id] = alert
                await self.daemon._send_alert(alert)
    
    async def _handle_application_event(self, event):
        """Handle application event log entries."""
        event_id = event.EventID
        source = event.SourceName
        
        try:
            if int(event_id) == 1001 and str(source).lower() == "windows error reporting":
                return
        except Exception:
            pass
        
        # Check for application crashes
        if event_id in self.critical_events.get('Application', {}):
            description = self.critical_events['Application'][event_id]
            
            alert_id = f"event_app_{source}_{event_id}_{int(event.TimeGenerated.timestamp())}"
            
            from app.agents.sentinel.sentinel_daemon import SentinelAlert
            
            alert = SentinelAlert(
                id=alert_id,
                type="application_event",
                severity="critical" if event_id in [1000, 1002] else "warning",
                message=f"Application Event ({source}): {description}",
                current_value=event_id,
                threshold=0,
                timestamp=event.TimeGenerated,
                suggestions=["restart_app", "check_logs", "ignore"],
                processes=[],
                user_id=None
            )
            
            try:
                if alert.severity == "warning" and any(
                    profile.get("gaming_mode") for profile in self.daemon.user_profiles.values()
                ):
                    return
            except Exception:
                pass
            
            if self.daemon._should_alert(f"event_app_{source}_{event_id}", datetime.utcnow()):
                self.daemon.last_alerts[f"event_app_{source}_{event_id}"] = datetime.utcnow()
                self.daemon.active_alerts[alert_id] = alert
                await self.daemon._send_alert(alert)
    
    async def _handle_security_event(self, event):
        """Handle security event log entries."""
        # Monitor for failed logins, privilege escalations, etc.
        event_id = event.EventID
        
        critical_security_events = {
            4625: "Failed login attempt",
            4648: "Explicit credentials used",
            4672: "Special privileges assigned",
            4673: "Privileged service called",
            4674: "Operation attempted on privileged object",
            4688: "Invalid token used",
            4720: "User account created",
            4722: "User account enabled",
            4723: "User account password change attempt",
            4724: "User account password reset attempt",
            4732: "Member added to security-enabled group",
            4740: "User account locked out",
            4768: "User account created",
            4769: "User account deleted",
            4770: "User account modified",
            4771: "User account password changed",
            4776: "Computer account added to domain",
            4778: "Computer account disabled",
            4779: "Computer account enabled",
            4780: "Computer account modified",
            4781: "Computer account deleted",
            4782: "Security group modified",
            4783: "Security group deleted",
            4784: "Security group modified",
            4785: "Security group deleted",
            4786: "Security group modified",
            4787: "Security group deleted",
            4788: "Security group modified",
            4789: "Security group deleted",
            4790: "Security group modified",
            4791: "Security group deleted",
            4792: "Security group modified",
            4793: "Security group deleted",
            4794: "Security group modified",
            4795: "Security group deleted",
            4796: "Security group modified",
            4797: "Security group deleted",
            4798: "Security group modified",
            4799: "Security group deleted",
            4800: "Security group modified",
            4801: "Security group deleted",
            4802: "Security group modified",
            4803: "Security group deleted",
        }
        
        if event_id in critical_security_events:
            description = critical_security_events[event_id]
            
            alert_id = f"event_security_{event_id}_{int(event.TimeGenerated.timestamp())}"
            
            from app.agents.sentinel.sentinel_daemon import SentinelAlert
            
            alert = SentinelAlert(
                id=alert_id,
                type="security_event",
                severity="warning",  # Security events are usually warnings
                message=f"Security Event: {description}",
                current_value=event_id,
                threshold=0,
                timestamp=event.TimeGenerated,
                suggestions=["investigate", "check_logs", "ignore"],
                processes=[],
                user_id=None
            )
            
            # Only alert for critical security events
            if event_id in [4625, 4648, 4672, 4740]:
                if self.daemon._should_alert(f"event_security_{event_id}", datetime.utcnow()):
                    self.daemon.last_alerts[f"event_security_{event_id}"] = datetime.utcnow()
                    self.daemon.active_alerts[alert_id] = alert
                    await self.daemon._send_alert(alert)
    
    def get_recent_events(self, hours: int = 1) -> List[Dict]:
        """Get recent events from all logs."""
        events = []
        
        if not EVENT_LOG_AVAILABLE or platform.system() != "Windows":
            return events
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for log_type in ["System", "Application"]:
                try:
                    server = None
                    log_handle = win32evtlog.OpenEventLog(server, log_type)
                    
                    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                    log_events = win32evtlog.ReadEventLog(log_handle, flags, 0)
                    
                    for event in log_events:
                        if event.TimeGenerated >= cutoff_time:
                            events.append({
                                "log_type": log_type,
                                "event_id": event.EventID,
                                "source": event.SourceName,
                                "time": event.TimeGenerated.isoformat(),
                                "category": event.EventCategory,
                                "computer": event.ComputerName,
                                "user": event.Sid,
                            })
                    
                    win32evtlog.CloseEventLog(log_handle)
                    
                except Exception as e:
                    logger.debug(f"[Sentinel] Failed to get {log_type} events: {e}")
        
        except Exception as e:
            logger.error(f"[Sentinel] Failed to get recent events: {e}")
        
        return events
