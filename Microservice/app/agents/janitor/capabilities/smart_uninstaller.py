"""
Smart Uninstaller - Tracks installed apps and detects unused ones.

Features:
- Scans installed programs from registry
- Tracks app usage (via prefetch files)
- Suggests unused apps for removal
- Can trigger uninstall process
"""

import os
import logging
import subprocess
import winreg
from datetime import datetime, timedelta
from typing import Optional

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


class SmartUninstallerCapability(BaseCapability):
    """Finds and helps uninstall unused programs."""
    
    name = "smart_uninstaller"
    description = "Detects unused programs and helps uninstall them"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self._prefetch_path = "C:\\Windows\\Prefetch"
        self._cache: dict = {}
        
        # Registry paths for installed programs
        self._registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """This capability doesn't analyze individual files."""
        return CapabilityResult(capability=self.name, action_required=False)
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Trigger uninstall for a program."""
        uninstall_string = result.metadata.get("uninstall_string")
        
        if not uninstall_string:
            return False
        
        try:
            # Launch uninstaller
            subprocess.Popen(uninstall_string, shell=True)
            logger.info(f"[SmartUninstaller] Launched uninstaller: {uninstall_string[:50]}...")
            return True
        except Exception as e:
            logger.error(f"[SmartUninstaller] Uninstall failed: {e}")
            return False
    
    async def scan(self) -> dict:
        """
        Scan installed programs and their usage.
        
        Returns list of programs with usage info.
        """
        logger.info("[SmartUninstaller] Scanning installed programs...")
        
        programs = await self._get_installed_programs()
        usage_data = await self._get_usage_data()
        
        # Merge usage data
        for program in programs:
            exe_name = program.get("display_name", "").replace(" ", "_").upper()
            
            # Try to find matching prefetch
            for prefetch_name, last_run in usage_data.items():
                if exe_name[:10] in prefetch_name:
                    program["last_used"] = last_run
                    program["days_unused"] = (datetime.now() - last_run).days
                    break
            else:
                program["last_used"] = None
                program["days_unused"] = -1  # Unknown
        
        # Sort by days unused (most unused first)
        programs.sort(key=lambda x: x.get("days_unused", -1), reverse=True)
        
        # Filter to unused (90+ days or unknown)
        unused = [p for p in programs if p.get("days_unused", -1) > 90 or p.get("days_unused", -1) == -1]
        
        total_size = sum(p.get("size_mb", 0) for p in unused)
        
        logger.info(f"[SmartUninstaller] Found {len(programs)} programs, {len(unused)} potentially unused")
        
        return {
            "total_programs": len(programs),
            "potentially_unused": len(unused),
            "unused_programs": unused[:20],  # Top 20
            "all_programs": programs,
            "potential_space_mb": round(total_size, 2),
        }
    
    async def _get_installed_programs(self) -> list[dict]:
        """Get list of installed programs from registry."""
        programs = []
        
        for hkey, subkey in self._registry_paths:
            try:
                key = winreg.OpenKey(hkey, subkey)
                
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        program_key = winreg.OpenKey(key, subkey_name)
                        
                        try:
                            name = winreg.QueryValueEx(program_key, "DisplayName")[0]
                        except:
                            continue
                        
                        try:
                            uninstall = winreg.QueryValueEx(program_key, "UninstallString")[0]
                        except:
                            uninstall = None
                        
                        try:
                            size = winreg.QueryValueEx(program_key, "EstimatedSize")[0]
                            size_mb = size / 1024  # KB to MB
                        except:
                            size_mb = 0
                        
                        try:
                            publisher = winreg.QueryValueEx(program_key, "Publisher")[0]
                        except:
                            publisher = "Unknown"
                        
                        try:
                            install_date = winreg.QueryValueEx(program_key, "InstallDate")[0]
                        except:
                            install_date = None
                        
                        programs.append({
                            "display_name": name,
                            "publisher": publisher,
                            "size_mb": round(size_mb, 2),
                            "uninstall_string": uninstall,
                            "install_date": install_date,
                        })
                        
                        winreg.CloseKey(program_key)
                    except:
                        pass
                
                winreg.CloseKey(key)
            except Exception as e:
                logger.debug(f"[SmartUninstaller] Registry error: {e}")
        
        # Remove duplicates
        seen = set()
        unique_programs = []
        for p in programs:
            if p["display_name"] not in seen:
                seen.add(p["display_name"])
                unique_programs.append(p)
        
        return unique_programs
    
    async def _get_usage_data(self) -> dict[str, datetime]:
        """Get app usage data from prefetch files."""
        usage = {}
        
        if not os.path.exists(self._prefetch_path):
            return usage
        
        try:
            for filename in os.listdir(self._prefetch_path):
                if filename.endswith(".pf"):
                    filepath = os.path.join(self._prefetch_path, filename)
                    try:
                        stat = os.stat(filepath)
                        last_run = datetime.fromtimestamp(stat.st_mtime)
                        
                        # Extract app name from prefetch filename
                        app_name = filename.rsplit("-", 1)[0]
                        usage[app_name] = last_run
                    except:
                        pass
        except PermissionError:
            logger.warning("[SmartUninstaller] Cannot access Prefetch (need admin)")
        
        return usage
    
    async def uninstall(self, program_name: str) -> dict:
        """
        Trigger uninstall for a specific program.
        
        Returns result of uninstall attempt.
        """
        # Find program
        programs = await self._get_installed_programs()
        
        for program in programs:
            if program_name.lower() in program["display_name"].lower():
                uninstall_string = program.get("uninstall_string")
                
                if not uninstall_string:
                    return {"success": False, "error": "No uninstall string found"}
                
                try:
                    subprocess.Popen(uninstall_string, shell=True)
                    return {
                        "success": True,
                        "program": program["display_name"],
                        "message": "Uninstaller launched",
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Program not found"}
