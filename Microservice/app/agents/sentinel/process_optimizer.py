"""
Process Optimizer - Advanced process priority and resource management.

Handles:
- Process priority adjustment (Windows priority classes)
- Resource hog identification and termination
- Ghost process cleanup (zombie processes)
- Focus mode optimization for target applications
- Background process throttling
"""

import psutil
import logging
import asyncio
import subprocess
import platform
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import ctypes
from ctypes import wintypes

logger = logging.getLogger(__name__)

# Windows API constants for process priority
PRIORITY_CLASSES = {
    "idle": 0x40,          # IDLE_PRIORITY_CLASS
    "below_normal": 0x4000,  # BELOW_NORMAL_PRIORITY_CLASS
    "normal": 0x20,        # NORMAL_PRIORITY_CLASS
    "above_normal": 0x8000,  # ABOVE_NORMAL_PRIORITY_CLASS
    "high": 0x80,          # HIGH_PRIORITY_CLASS
    "realtime": 0x100,     # REALTIME_PRIORITY_CLASS
}

# Windows API functions
if platform.system() == "Windows":
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetPriorityClass.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        WINDOWS_API_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Windows API not available: {e}")
        WINDOWS_API_AVAILABLE = False
else:
    WINDOWS_API_AVAILABLE = False


class ProcessOptimizer:
    """
    Advanced process optimization with Windows API integration.
    
    Features:
    - Process priority management
    - Resource hog termination
    - Ghost process cleanup
    - Focus mode for target applications
    """
    
    def __init__(self):
        self._optimization_history = []
        self._protected_processes = {
            # Critical system processes
            "system", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
            "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe",
            # Common essential apps
            "chrome.exe", "firefox.exe", "code.exe", "devenv.exe", "msedge.exe"
        }
    
    async def optimize_for_focus(self, target_app: str) -> Dict[str, Any]:
        """
        Optimize system for a specific target application.
        
        Args:
            target_app: Name or partial name of target application
            
        Returns:
            Dict with optimization results and changes made
        """
        logger.info(f"[Sentinel] Optimizing for focus app: {target_app}")
        
        optimization_result = {
            "target_app": target_app,
            "timestamp": datetime.utcnow().isoformat(),
            "actions_taken": [],
            "processes_adjusted": [],
            "success": False,
        }
        
        try:
            # Find target process
            target_process = await self._find_target_process(target_app)
            if not target_process:
                optimization_result["actions_taken"].append(f"Target process '{target_app}' not found")
                return optimization_result
            
            optimization_result["target_process"] = target_process
            
            # Set target process to HIGH priority
            priority_result = await self._set_process_priority(target_process["pid"], "high")
            if priority_result["success"]:
                optimization_result["actions_taken"].append(f"Set {target_app} to HIGH priority")
                optimization_result["processes_adjusted"].append({
                    "pid": target_process["pid"],
                    "name": target_process["name"],
                    "action": "priority_high",
                    "success": True
                })
            
            # Identify and throttle background processes
            background_hogs = await self._identify_background_hogs(target_process["pid"])
            for hog in background_hogs:
                # Try to set to LOW priority first
                priority_result = await self._set_process_priority(hog["pid"], "below_normal")
                if priority_result["success"]:
                    optimization_result["actions_taken"].append(f"Set {hog['name']} to LOW priority")
                    optimization_result["processes_adjusted"].append({
                        "pid": hog["pid"],
                        "name": hog["name"],
                        "action": "priority_low",
                        "success": True,
                        "reason": f"CPU usage: {hog['cpu_percent']}%"
                    })
            
            optimization_result["success"] = True
            self._optimization_history.append(optimization_result)
            
            logger.info(f"[Sentinel] Focus optimization complete: {len(optimization_result['processes_adjusted'])} processes adjusted")
            
        except Exception as e:
            logger.error(f"[Sentinel] Focus optimization failed: {e}")
            optimization_result["error"] = str(e)
        
        return optimization_result
    
    async def kill_resource_hogs(self, cpu_threshold: float = 90.0, memory_threshold: float = 95.0) -> Dict[str, Any]:
        """
        Identify and terminate resource hog processes.
        
        Args:
            cpu_threshold: CPU usage percentage threshold
            memory_threshold: Memory usage percentage threshold
            
        Returns:
            Dict with termination results
        """
        logger.info(f"[Sentinel] Hunting resource hogs (CPU>{cpu_threshold}%, Memory>{memory_threshold}%)")
        
        termination_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "thresholds": {"cpu": cpu_threshold, "memory": memory_threshold},
            "processes_killed": [],
            "processes_skipped": [],
            "success": True,
        }
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
                try:
                    cpu = proc.info['cpu_percent'] or 0.0
                    memory = proc.info['memory_percent'] or 0.0
                    
                    # Check if process exceeds thresholds
                    if cpu > cpu_threshold or memory > memory_threshold:
                        process_name = proc.info['name'].lower()
                        
                        # Skip protected processes
                        if self._is_protected_process(process_name):
                            termination_result["processes_skipped"].append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name'],
                                "reason": "protected_process",
                                "cpu": cpu,
                                "memory": memory
                            })
                            continue
                        
                        # Terminate the process
                        kill_result = await self._terminate_process(proc.info['pid'], proc.info['name'])
                        if kill_result["success"]:
                            termination_result["processes_killed"].append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name'],
                                "cpu": cpu,
                                "memory": memory,
                                "reason": f"CPU:{cpu}%>MEM:{memory}%"
                            })
                        else:
                            termination_result["processes_skipped"].append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name'],
                                "reason": kill_result.get("reason", "termination_failed"),
                                "cpu": cpu,
                                "memory": memory
                            })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        
        except Exception as e:
            logger.error(f"[Sentinel] Resource hog termination failed: {e}")
            termination_result["success"] = False
            termination_result["error"] = str(e)
        
        logger.info(f"[Sentinel] Resource hog hunt complete: {len(termination_result['processes_killed'])} killed, {len(termination_result['processes_skipped'])} skipped")
        
        return termination_result
    
    async def cleanup_ghost_processes(self, idle_hours: float = 2.0) -> Dict[str, Any]:
        """
        Find and clean up ghost processes (zombie/idle processes).
        
        Args:
            idle_hours: Minimum hours of inactivity to consider a process as ghost
            
        Returns:
            Dict with cleanup results
        """
        logger.info(f"[Sentinel] Ghost process cleanup (idle > {idle_hours}h)")
        
        cleanup_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "idle_threshold_hours": idle_hours,
            "processes_cleaned": [],
            "processes_skipped": [],
            "success": True,
        }
        
        try:
            current_time = datetime.now()
            idle_threshold = timedelta(hours=idle_hours)
            
            for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cpu_percent', 'memory_percent', 'status', 'username']):
                try:
                    # Skip if process has recent activity
                    cpu = proc.info['cpu_percent'] or 0.0
                    if cpu > 0.1:  # Has recent CPU activity
                        continue
                    
                    # Check process age
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    process_age = current_time - create_time
                    
                    if process_age < idle_threshold:
                        continue
                    
                    # Check if process has no visible window (background process)
                    if not await self._is_background_process(proc.info['pid']):
                        continue
                    
                    process_name = proc.info['name'].lower()
                    
                    # Skip protected processes
                    if self._is_protected_process(process_name):
                        cleanup_result["processes_skipped"].append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "reason": "protected_process",
                            "age_hours": process_age.total_seconds() / 3600
                        })
                        continue
                    
                    # Terminate the ghost process
                    kill_result = await self._terminate_process(proc.info['pid'], proc.info['name'])
                    if kill_result["success"]:
                        cleanup_result["processes_cleaned"].append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "age_hours": round(process_age.total_seconds() / 3600, 2),
                            "memory_mb": round((proc.info['memory_percent'] or 0) * psutil.virtual_memory().total / 100 / (1024**2), 2)
                        })
                    else:
                        cleanup_result["processes_skipped"].append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "reason": kill_result.get("reason", "termination_failed"),
                            "age_hours": round(process_age.total_seconds() / 3600, 2)
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        
        except Exception as e:
            logger.error(f"[Sentinel] Ghost process cleanup failed: {e}")
            cleanup_result["success"] = False
            cleanup_result["error"] = str(e)
        
        logger.info(f"[Sentinel] Ghost cleanup complete: {len(cleanup_result['processes_cleaned'])} cleaned, {len(cleanup_result['processes_skipped'])} skipped")
        
        return cleanup_result
    
    async def _find_target_process(self, target_app: str) -> Optional[Dict[str, Any]]:
        """Find process by name or partial name."""
        target_lower = target_app.lower()
        
        best_match = None
        best_score = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                process_name = proc.info['name'].lower()
                
                # Exact match gets highest score
                if process_name == target_lower:
                    return {
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'] or 0.0,
                        "memory_percent": proc.info['memory_percent'] or 0.0,
                        "status": proc.info['status'],
                    }
                
                # Partial match scoring
                if target_lower in process_name:
                    score = len(target_lower) / len(process_name)
                    if score > best_score:
                        best_score = score
                        best_match = {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cpu_percent": proc.info['cpu_percent'] or 0.0,
                            "memory_percent": proc.info['memory_percent'] or 0.0,
                            "status": proc.info['status'],
                        }
            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return best_match
    
    async def _identify_background_hogs(self, target_pid: int, cpu_threshold: float = 5.0) -> List[Dict[str, Any]]:
        """Identify background processes using significant resources."""
        background_hogs = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
            try:
                # Skip target process itself
                if proc.info['pid'] == target_pid:
                    continue
                
                cpu = proc.info['cpu_percent'] or 0.0
                memory = proc.info['memory_percent'] or 0.0
                
                # Check if process is using significant resources
                if cpu > cpu_threshold or memory > cpu_threshold:
                    process_name = proc.info['name'].lower()
                    
                    # Skip protected processes
                    if self._is_protected_process(process_name):
                        continue
                    
                    background_hogs.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": cpu,
                        "memory_percent": memory,
                        "status": proc.info['status'],
                    })
            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by resource usage (highest first)
        background_hogs.sort(key=lambda x: (x['cpu_percent'], x['memory_percent']), reverse=True)
        
        return background_hogs[:10]  # Limit to top 10
    
    async def _set_process_priority(self, pid: int, priority: str) -> Dict[str, Any]:
        """Set process priority using Windows API."""
        if not WINDOWS_API_AVAILABLE:
            return {"success": False, "reason": "Windows API not available"}
        
        if priority not in PRIORITY_CLASSES:
            return {"success": False, "reason": f"Invalid priority: {priority}"}
        
        try:
            # Open process handle
            process_handle = kernel32.OpenProcess(0x200, False, pid)  # PROCESS_SET_INFORMATION
            if not process_handle:
                return {"success": False, "reason": "Failed to open process"}
            
            # Set priority class
            priority_class = PRIORITY_CLASSES[priority]
            result = kernel32.SetPriorityClass(process_handle, priority_class)
            
            # Close handle
            kernel32.CloseHandle(process_handle)
            
            if result:
                logger.debug(f"[Sentinel] Set PID {pid} priority to {priority}")
                return {"success": True}
            else:
                return {"success": False, "reason": "SetPriorityClass failed"}
        
        except Exception as e:
            logger.error(f"[Sentinel] Priority setting failed for PID {pid}: {e}")
            return {"success": False, "reason": str(e)}
    
    async def _terminate_process(self, pid: int, name: str) -> Dict[str, Any]:
        """Safely terminate a process."""
        try:
            process = psutil.Process(pid)
            
            # Try graceful termination first
            process.terminate()
            
            # Wait up to 5 seconds for graceful termination
            try:
                process.wait(timeout=5)
                logger.info(f"[Sentinel] Gracefully terminated PID {pid} ({name})")
                return {"success": True, "method": "graceful"}
            except psutil.TimeoutExpired:
                # Force kill if graceful termination fails
                process.kill()
                logger.info(f"[Sentinel] Force killed PID {pid} ({name})")
                return {"success": True, "method": "force"}
        
        except psutil.NoSuchProcess:
            return {"success": True, "reason": "process_already_terminated"}
        except psutil.AccessDenied:
            return {"success": False, "reason": "access_denied"}
        except Exception as e:
            logger.error(f"[Sentinel] Process termination failed for PID {pid}: {e}")
            return {"success": False, "reason": str(e)}
    
    async def _is_background_process(self, pid: int) -> bool:
        """Check if process has no visible window (background process)."""
        if platform.system() != "Windows":
            return True  # Assume background on non-Windows
        
        try:
            # Use Windows API to check for visible windows
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # Enumerate windows for this process
            def callback(hwnd, lparam):
                window_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                
                if window_pid.value == pid:
                    # Check if window is visible
                    if user32.IsWindowVisible(hwnd):
                        return False  # Found visible window
            
            # This is a simplified check - in reality would need more complex window enumeration
            return True  # Assume background for now
        
        except Exception:
            return True  # If we can't determine, assume background
    
    def _is_protected_process(self, process_name: str) -> bool:
        """Check if process is in the protected list."""
        return process_name in self._protected_processes
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get recent optimization history."""
        return self._optimization_history[-10:]  # Return last 10 optimizations
