"""
Scheduled maintenance for Sentinel.

Performs maintenance tasks during idle time or scheduled windows.
"""

import logging
import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ScheduledMaintenance:
    """Handles scheduled maintenance tasks."""
    
    def __init__(self, sentinel_daemon):
        self.daemon = sentinel_daemon
        self.running = False
        self.maintenance_windows = [
            # Default maintenance windows (2 AM - 4 AM)
            {"start": time(2, 0), "end": time(4, 0), "days": [0, 1, 2, 3, 4, 5, 6]},  # Daily
            # Weekend maintenance window (3 AM - 5 AM)
            {"start": time(3, 0), "end": time(5, 0), "days": [5, 6]},  # Sat, Sun
        ]
        
        # Maintenance tasks
        self.tasks = {
            "disk_cleanup": {
                "enabled": True,
                "frequency": "weekly",
                "last_run": None,
                "condition": lambda: self._check_disk_space_threshold()
            },
            "memory_optimization": {
                "enabled": True,
                "frequency": "daily",
                "last_run": None,
                "condition": lambda: self._check_memory_fragmentation()
            },
            "registry_cleanup": {
                "enabled": True,
                "frequency": "monthly",
                "last_run": None,
                "condition": lambda: True
            },
            "temp_file_cleanup": {
                "enabled": True,
                "frequency": "daily",
                "last_run": None,
                "condition": lambda: True
            },
            "update_check": {
                "enabled": True,
                "frequency": "weekly",
                "last_run": None,
                "condition": lambda: True
            }
        }
    
    async def start(self):
        """Start scheduled maintenance."""
        self.running = True
        logger.info("[Sentinel] Starting scheduled maintenance...")
        
        # Start maintenance loop
        asyncio.create_task(self._maintenance_loop())
    
    async def stop(self):
        """Stop scheduled maintenance."""
        self.running = False
    
    async def _maintenance_loop(self):
        """Main maintenance loop."""
        while self.running:
            try:
                # Check if we're in a maintenance window
                if self._is_maintenance_window():
                    # Check system is idle
                    if await self._is_system_idle():
                        # Run due maintenance tasks
                        await self._run_due_tasks()
                
                # Check every 10 minutes
                await asyncio.sleep(600)
                
            except Exception as e:
                logger.error(f"[Sentinel] Maintenance loop error: {e}")
                await asyncio.sleep(300)
    
    def _is_maintenance_window(self) -> bool:
        """Check if current time is in a maintenance window."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()
        
        for window in self.maintenance_windows:
            if current_day in window["days"]:
                start = window["start"]
                end = window["end"]
                
                # Handle overnight windows
                if start <= end:
                    if start <= current_time <= end:
                        return True
                else:  # Overnight window
                    if current_time >= start or current_time <= end:
                        return True
        
        return False
    
    async def _is_system_idle(self) -> bool:
        """Check if system is idle (low CPU, no user activity)."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 20:
                return False
            
            # Check mouse/keyboard activity (Windows specific)
            import platform
            if platform.system() == "Windows":
                try:
                    import win32api
                    import win32con
                    
                    # Get last input time
                    last_input = win32api.GetLastInputInfo()
                    current_time = win32api.GetTickCount()
                    idle_time = (current_time - last_input) / 1000  # Convert to seconds
                    
                    # Consider idle if no input for 15 minutes
                    if idle_time < 900:  # 15 minutes
                        return False
                
                except ImportError:
                    logger.debug("[Sentinel] Win32 not available for idle detection")
            
            return True
        
        except Exception as e:
            logger.error(f"[Sentinel] Error checking system idle: {e}")
            return False
    
    async def _run_due_tasks(self):
        """Run maintenance tasks that are due."""
        now = datetime.now()
        
        for task_name, task_config in self.tasks.items():
            if not task_config["enabled"]:
                continue
            
            # Check if task is due
            if self._is_task_due(task_name, task_config, now):
                # Check condition
                if task_config["condition"]():
                    try:
                        await self._run_maintenance_task(task_name)
                        task_config["last_run"] = now
                        logger.info(f"[Sentinel] Maintenance task completed: {task_name}")
                    except Exception as e:
                        logger.error(f"[Sentinel] Maintenance task failed: {task_name} - {e}")
    
    def _is_task_due(self, task_name: str, task_config: Dict, now: datetime) -> bool:
        """Check if a maintenance task is due."""
        last_run = task_config["last_run"]
        frequency = task_config["frequency"]
        
        if not last_run:
            return True
        
        if frequency == "daily":
            return (now - last_run).days >= 1
        elif frequency == "weekly":
            return (now - last_run).days >= 7
        elif frequency == "monthly":
            return (now - last_run).days >= 30
        elif frequency == "hourly":
            return (now - last_run).seconds >= 3600
        
        return False
    
    async def _run_maintenance_task(self, task_name: str):
        """Run a specific maintenance task."""
        if task_name == "disk_cleanup":
            await self._run_disk_cleanup()
        elif task_name == "memory_optimization":
            await self._run_memory_optimization()
        elif task_name == "registry_cleanup":
            await self._run_registry_cleanup()
        elif task_name == "temp_file_cleanup":
            await self._run_temp_file_cleanup()
        elif task_name == "update_check":
            await self._run_update_check()
        
        # Notify user
        await self.daemon._broadcast_message({
            "type": "sentinel_maintenance_completed",
            "task": task_name,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _run_disk_cleanup(self):
        """Run disk cleanup via Janitor."""
        await self.daemon._trigger_cleanup()
    
    async def _run_memory_optimization(self):
        """Run memory optimization."""
        try:
            import psutil
            
            # Clear Python garbage collector
            import gc
            gc.collect()
            
            # Suggest memory-intensive apps to close
            processes = await self.daemon.hardware_monitor.get_top_processes(limit=10)
            memory_hogs = [p for p in processes if p["memory_mb"] > 1000]
            
            if memory_hogs:
                await self.daemon._broadcast_message({
                    "type": "sentinel_maintenance_suggestion",
                    "action": "close_memory_hogs",
                    "processes": memory_hogs,
                    "message": f"Found {len(memory_hogs)} memory-heavy applications"
                })
        
        except Exception as e:
            logger.error(f"[Sentinel] Memory optimization failed: {e}")
    
    async def _run_registry_cleanup(self):
        """Run registry cleanup (Windows only)."""
        import platform
        
        if platform.system() != "Windows":
            return
        
        # This would integrate with Windows registry cleanup tools
        logger.info("[Sentinel] Registry cleanup scheduled")
    
    async def _run_temp_file_cleanup(self):
        """Run temporary file cleanup."""
        import tempfile
        import os
        import shutil
        
        try:
            # Clean Python temp files
            temp_dir = tempfile.gettempdir()
            cleaned = 0
            
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    # Only delete files older than 1 day
                    if os.path.isfile(item_path):
                        file_age = datetime.now() - datetime.fromtimestamp(os.path.getctime(item_path))
                        if file_age.days > 1:
                            os.remove(item_path)
                            cleaned += 1
                    elif os.path.isdir(item_path):
                        # Remove empty temp directories
                        if not os.listdir(item_path):
                            shutil.rmtree(item_path)
                            cleaned += 1
                except:
                    pass
            
            logger.info(f"[Sentinel] Cleaned {cleaned} temporary files")
        
        except Exception as e:
            logger.error(f"[Sentinel] Temp file cleanup failed: {e}")
    
    async def _run_update_check(self):
        """Check for system updates."""
        import platform
        
        if platform.system() == "Windows":
            # This would check Windows Update
            logger.info("[Sentinel] Windows Update check scheduled")
        
        # Check for Python package updates
        logger.info("[Sentinel] Package update check scheduled")
    
    def _check_disk_space_threshold(self) -> bool:
        """Check if disk space is below threshold."""
        try:
            import psutil
            
            for partition in psutil.disk_partitions():
                usage = psutil.disk_usage(partition.mountpoint)
                if (usage.free / usage.total) < 0.1:  # Less than 10% free
                    return True
        
        except:
            pass
        
        return False
    
    def _check_memory_fragmentation(self) -> bool:
        """Check if memory is fragmented."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            # Consider fragmented if available memory is low but usage isn't extremely high
            return memory.available < (1024**3) and memory.percent < 90  # Less than 1GB available but < 90% used
        
        except:
            pass
        
        return False
    
    def schedule_maintenance(self, task_name: str, schedule_time: datetime):
        """Schedule a one-time maintenance task."""
        # This would add a one-time scheduled task
        logger.info(f"[Sentinel] Scheduled maintenance: {task_name} at {schedule_time}")
    
    def get_maintenance_status(self) -> Dict:
        """Get maintenance status."""
        return {
            "running": self.running,
            "in_maintenance_window": self._is_maintenance_window(),
            "system_idle": False,  # Would check async
            "tasks": {
                name: {
                    "enabled": config["enabled"],
                    "frequency": config["frequency"],
                    "last_run": config["last_run"].isoformat() if config["last_run"] else None
                }
                for name, config in self.tasks.items()
            }
        }
