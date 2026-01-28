"""
Gaming mode detection for Sentinel.

Automatically detects when user is gaming and adjusts monitoring behavior.
"""

import logging
import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class GamingModeDetector:
    """Detects gaming mode and adjusts Sentinel behavior."""
    
    def __init__(self, sentinel_daemon):
        self.daemon = sentinel_daemon
        self.running = False
        self.is_gaming = False
        self.last_check = datetime.utcnow()
        
        # Known gaming processes
        self.gaming_processes = {
            # Steam games
            "steam.exe",
            "gameoverlayui.exe",
            # Epic Games
            "epicgameslauncher.exe",
            # Ubisoft
            "uplay.exe",
            # Origin
            "origin.exe",
            # Battle.net
            "battle.net.exe",
            # Common game launchers
            "gog galaxy.exe",
            "minecraft.exe",
            "robloxplayerbeta.exe",
            # Popular games
            "valorant.exe",
            "league of legends.exe",
            "cs2.exe",
            "dota2.exe",
            "overwatch.exe",
            "fortnite.exe",
            "apex.exe",
            "cod.exe",
            "fifa.exe",
            "nba2k.exe",
            "gta5.exe",
            "rdr2.exe",
            "cyberpunk2077.exe",
            "witcher3.exe",
            "skyrim.exe",
            "fallout4.exe",
            "doom.exe",
            "quake.exe",
            "halo.exe",
            "mass effect.exe",
            "dragon age.exe",
            "bioshock.exe",
            "portal2.exe",
            "half-life.exe",
            "left4dead2.exe",
            "team fortress 2.exe",
            "csgo.exe",
            "rust.exe",
            "ark.exe",
            "7daystodie.exe",
            "valheim.exe",
            "phasmophobia.exe",
            "among us.exe",
            "fall guys.exe",
            "rocket league.exe",
            "minecraftlauncher.exe",
        }
        
        # Gaming indicators
        self.gaming_indicators = {
            "high_gpu_usage": False,
            "high_cpu_usage": False,
            "full_screen_apps": [],
            "game_controllers": False,
            "low_background_processes": False
        }
    
    async def start(self):
        """Start gaming mode detection."""
        self.running = True
        logger.info("[Sentinel] Starting gaming mode detection...")
        
        # Start detection loop
        asyncio.create_task(self._detection_loop())
    
    async def stop(self):
        """Stop gaming mode detection."""
        self.running = False
    
    async def _detection_loop(self):
        """Main detection loop."""
        while self.running:
            try:
                was_gaming = self.is_gaming
                self.is_gaming = await self._detect_gaming_mode()
                
                # Update user profiles if gaming mode changed
                if was_gaming != self.is_gaming:
                    await self._update_gaming_status()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"[Sentinel] Gaming detection error: {e}")
                await asyncio.sleep(60)
    
    async def _detect_gaming_mode(self) -> bool:
        """Detect if user is currently gaming."""
        gaming_score = 0
        
        # Check for gaming processes
        gaming_processes = await self._check_gaming_processes()
        if gaming_processes:
            gaming_score += 3
            logger.debug(f"[Sentinel] Gaming processes detected: {gaming_processes}")
        
        # Check GPU usage (if available)
        gpu_usage = await self._check_gpu_usage()
        if gpu_usage > 80:  # High GPU usage
            gaming_score += 2
            self.gaming_indicators["high_gpu_usage"] = True
        
        # Check full-screen applications
        full_screen = await self._check_full_screen_apps()
        if full_screen:
            gaming_score += 2
            self.gaming_indicators["full_screen_apps"] = full_screen
        
        # Check for game controllers
        controllers = await self._check_game_controllers()
        if controllers:
            gaming_score += 1
            self.gaming_indicators["game_controllers"] = True
        
        # Check system state
        system_state = await self._check_system_state()
        if system_state["low_background"]:
            gaming_score += 1
            self.gaming_indicators["low_background_processes"] = True
        
        # Gaming mode if score >= 3
        is_gaming = gaming_score >= 3
        
        if is_gaming != self.is_gaming:
            logger.info(f"[Sentinel] Gaming mode detected: {is_gaming} (score: {gaming_score})")
        
        return is_gaming
    
    async def _check_gaming_processes(self) -> List[str]:
        """Check for running gaming processes."""
        gaming_procs = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = (proc.info.get('name') or '').lower().strip()
                    if not name:
                        continue
                    if name in self.gaming_processes:
                        gaming_procs.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"[Sentinel] Error checking gaming processes: {e}")
        
        return gaming_procs
    
    async def _check_gpu_usage(self) -> float:
        """Check GPU usage (Windows only)."""
        try:
            import platform
            if platform.system() != "Windows":
                return 0
            
            # Try to get GPU usage via WMI
            import wmi
            c = wmi.WMI()
            
            for gpu in c.query("SELECT * FROM Win32_VideoController"):
                adapter_ram = getattr(gpu, 'AdapterRAM', 0)
                if adapter_ram > 0:  # GPU with memory
                    # This is a rough estimate - actual GPU usage requires specialized libraries
                    return 50  # Placeholder
            
        except Exception as e:
            logger.debug(f"[Sentinel] GPU check failed: {e}")
        
        return 0
    
    async def _check_full_screen_apps(self) -> List[str]:
        """Check for full-screen applications."""
        full_screen_apps = []
        
        try:
            import platform
            if platform.system() != "Windows":
                return full_screen_apps
            
            # Check window states (simplified)
            import win32gui
            import win32con
            import win32api
            
            def enum_windows_callback(hwnd, apps):
                if win32gui.IsWindowVisible(hwnd):
                    rect = win32gui.GetWindowRect(hwnd)
                    screen_width = win32api.GetSystemMetrics(0)
                    screen_height = win32api.GetSystemMetrics(1)
                    
                    # Check if window is full screen
                    if (rect[0] == 0 and rect[1] == 0 and 
                        rect[2] == screen_width and rect[3] == screen_height):
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title:
                            apps.append(window_title)
                return True
            
            win32gui.EnumWindows(enum_windows_callback, full_screen_apps)
            
        except Exception as e:
            logger.debug(f"[Sentinel] Full screen check failed: {e}")
        
        return full_screen_apps
    
    async def _check_game_controllers(self) -> bool:
        """Check for connected game controllers."""
        try:
            import platform
            if platform.system() != "Windows":
                return False
            
            # Check for game controllers via Windows API
            import win32api
            import win32con
            
            # Get number of game controllers
            controllers = win32api.joyGetNumDevs()
            return controllers > 0
            
        except Exception as e:
            logger.debug(f"[Sentinel] Controller check failed: {e}")
        
        return False
    
    async def _check_system_state(self) -> Dict[str, bool]:
        """Check system state indicators."""
        state = {
            "low_background": False,
            "high_cpu": False,
            "high_memory": False
        }
        
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            state["high_cpu"] = cpu_percent > 70
            
            # Check memory usage
            memory = psutil.virtual_memory()
            state["high_memory"] = memory.percent > 80
            
            # Check number of background processes
            process_count = len(psutil.pids())
            state["low_background"] = process_count < 100  # Fewer processes when gaming
            
        except Exception as e:
            logger.debug(f"[Sentinel] System state check failed: {e}")
        
        return state
    
    async def _update_gaming_status(self):
        """Update gaming status for all users."""
        for user_id, profile in self.daemon.user_profiles.items():
            profile["gaming_mode"] = self.is_gaming
            
            # Adjust thresholds based on gaming mode
            if self.is_gaming:
                logger.info(f"[Sentinel] Gaming mode activated for {user_id} - suppressing non-critical alerts")
            else:
                logger.info(f"[Sentinel] Gaming mode deactivated for {user_id} - normal monitoring resumed")
    
    def get_gaming_status(self) -> Dict:
        """Get current gaming mode status."""
        return {
            "is_gaming": self.is_gaming,
            "indicators": self.gaming_indicators,
            "last_check": self.last_check.isoformat(),
            "gaming_processes": self.gaming_processes
        }
    
    def add_gaming_process(self, process_name: str):
        """Add a custom gaming process."""
        self.gaming_processes.add(process_name.lower())
        logger.info(f"[Sentinel] Added custom gaming process: {process_name}")
    
    def remove_gaming_process(self, process_name: str):
        """Remove a gaming process."""
        self.gaming_processes.discard(process_name.lower())
        logger.info(f"[Sentinel] Removed gaming process: {process_name}")
