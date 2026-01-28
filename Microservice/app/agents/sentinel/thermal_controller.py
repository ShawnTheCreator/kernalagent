"""
Thermal Controller - Advanced temperature and power management.

Handles:
- CPU/GPU temperature monitoring
- Fan curve adjustment (where supported)
- Thermal throttling and process priority adjustment
- Power profile management (Windows power schemes)
- Heat source identification and mitigation
"""

import logging
import asyncio
import subprocess
import platform
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Windows power scheme GUIDs
POWER_SCHEMES = {
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
}

# Temperature thresholds
TEMP_THRESHOLDS = {
    "warning": 80.0,    # °C - Start monitoring closely
    "critical": 85.0,    # °C - Take action
    "emergency": 90.0,  # °C - Aggressive action
    "shutdown": 95.0,    # °C - System at risk
}


class ThermalController:
    """
    Advanced thermal management with power profile control.
    
    Features:
    - Real-time temperature monitoring
    - Automatic power profile switching
    - Heat source process identification
    - Thermal throttling through priority adjustment
    """
    
    def __init__(self):
        self._current_power_scheme = None
        self._thermal_history = []
        self._last_profile_change = None
        self._profile_cooldown = timedelta(minutes=5)  # Prevent rapid switching
        
        # Initialize current power scheme
        if platform.system() == "Windows":
            self._current_power_scheme = self._get_current_power_scheme()
    
    async def monitor_and_control(self, temperature_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor temperatures and take appropriate action.
        
        Args:
            temperature_data: Temperature sensor data from hardware monitor
            
        Returns:
            Dict with actions taken and thermal status
        """
        timestamp = datetime.utcnow()
        max_temp = temperature_data.get("max_temp", 0)
        
        control_result = {
            "timestamp": timestamp.isoformat(),
            "max_temperature": max_temp,
            "actions_taken": [],
            "thermal_state": self._get_thermal_state(max_temp),
            "success": True,
        }
        
        try:
            # Record thermal history
            self._thermal_history.append({
                "timestamp": timestamp,
                "max_temp": max_temp,
                "sensors": temperature_data.get("sensors", {})
            })
            
            # Keep history limited
            if len(self._thermal_history) > 100:
                self._thermal_history = self._thermal_history[-100:]
            
            # Take action based on temperature level
            if max_temp >= TEMP_THRESHOLDS["emergency"]:
                await self._handle_emergency_temperature(control_result)
            elif max_temp >= TEMP_THRESHOLDS["critical"]:
                await self._handle_critical_temperature(control_result)
            elif max_temp >= TEMP_THRESHOLDS["warning"]:
                await self._handle_warning_temperature(control_result)
            
            # Check if we can return to normal power profile
            elif max_temp < TEMP_THRESHOLDS["warning"] - 5:  # 5°C hysteresis
                await self._handle_normal_temperature(control_result)
        
        except Exception as e:
            logger.error(f"[Sentinel] Thermal control failed: {e}")
            control_result["success"] = False
            control_result["error"] = str(e)
        
        return control_result
    
    async def set_power_profile(self, profile: str) -> Dict[str, Any]:
        """
        Set Windows power profile.
        
        Args:
            profile: "balanced", "power_saver", or "high_performance"
            
        Returns:
            Dict with operation result
        """
        if platform.system() != "Windows":
            return {"success": False, "reason": "Power profile control only available on Windows"}
        
        if profile not in POWER_SCHEMES:
            return {"success": False, "reason": f"Invalid power profile: {profile}"}
        
        # Check cooldown period
        if self._last_profile_change:
            time_since_change = datetime.now() - self._last_profile_change
            if time_since_change < self._profile_cooldown:
                return {
                    "success": False, 
                    "reason": f"Profile change cooldown active ({self._profile_cooldown.total_seconds()}s)"
                }
        
        try:
            guid = POWER_SCHEMES[profile]
            command = f'powercfg /setactive {guid}'
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self._current_power_scheme = profile
                self._last_profile_change = datetime.now()
                logger.info(f"[Sentinel] Power profile changed to: {profile}")
                return {"success": True, "profile": profile, "previous": self._current_power_scheme}
            else:
                logger.error(f"[Sentinel] Power profile change failed: {result.stderr}")
                return {"success": False, "reason": result.stderr}
        
        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "Power profile command timed out"}
        except Exception as e:
            logger.error(f"[Sentinel] Power profile change error: {e}")
            return {"success": False, "reason": str(e)}
    
    async def identify_heat_sources(self, process_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify processes likely contributing to high temperatures.
        
        Args:
            process_data: List of processes with resource usage
            
        Returns:
            List of potential heat sources sorted by likelihood
        """
        heat_sources = []
        
        for proc in process_data:
            # Calculate heat score based on CPU usage and memory
            cpu_score = proc.get("cpu_percent", 0) * 2  # CPU is primary heat source
            memory_score = proc.get("memory_percent", 0) * 0.5  # Memory contributes less
            heat_score = cpu_score + memory_score
            
            # Only consider processes with significant resource usage
            if heat_score > 10:  # Threshold for heat contribution
                heat_sources.append({
                    "pid": proc["pid"],
                    "name": proc["name"],
                    "cpu_percent": proc["cpu_percent"],
                    "memory_percent": proc.get("memory_percent", 0),
                    "heat_score": round(heat_score, 2),
                    "status": proc.get("status", "unknown"),
                })
        
        # Sort by heat score (highest first)
        heat_sources.sort(key=lambda x: x["heat_score"], reverse=True)
        
        return heat_sources[:5]  # Return top 5 heat sources
    
    async def _handle_emergency_temperature(self, control_result: Dict[str, Any]):
        """Handle emergency temperature (>90°C)."""
        logger.warning(f"[Sentinel] EMERGENCY temperature: {control_result['max_temperature']}°C")
        
        # Switch to power saver mode immediately
        profile_result = await self.set_power_profile("power_saver")
        if profile_result["success"]:
            control_result["actions_taken"].append("Switched to Power Saver profile")
        
        # Note: Process throttling would be handled by ProcessOptimizer
        control_result["actions_taken"].append("Emergency thermal protocol activated")
    
    async def _handle_critical_temperature(self, control_result: Dict[str, Any]):
        """Handle critical temperature (>85°C)."""
        logger.warning(f"[Sentinel] CRITICAL temperature: {control_result['max_temperature']}°C")
        
        # Switch to balanced mode if not already
        if self._current_power_scheme != "power_saver":
            profile_result = await self.set_power_profile("balanced")
            if profile_result["success"]:
                control_result["actions_taken"].append("Switched to Balanced profile")
        
        control_result["actions_taken"].append("Critical thermal protocol activated")
    
    async def _handle_warning_temperature(self, control_result: Dict[str, Any]):
        """Handle warning temperature (>80°C)."""
        logger.info(f"[Sentinel] WARNING temperature: {control_result['max_temperature']}°C")
        
        # Monitor closely, no automatic action unless sustained
        recent_temps = [h["max_temp"] for h in self._thermal_history[-10:]]  # Last 10 readings
        if len(recent_temps) >= 5 and all(t >= TEMP_THRESHOLDS["warning"] for t in recent_temps):
            # Sustained high temperature - consider power profile change
            if self._current_power_scheme == "high_performance":
                profile_result = await self.set_power_profile("balanced")
                if profile_result["success"]:
                    control_result["actions_taken"].append("Switched to Balanced due to sustained high temp")
        
        control_result["actions_taken"].append("Thermal warning monitoring activated")
    
    async def _handle_normal_temperature(self, control_result: Dict[str, Any]):
        """Handle normal temperature (<75°C)."""
        # Check if we can return to high performance
        if self._current_power_scheme != "high_performance":
            # Only switch back if we've been cool for a while
            recent_temps = [h["max_temp"] for h in self._thermal_history[-20:]]  # Last 20 readings
            if len(recent_temps) >= 10 and all(t < TEMP_THRESHOLDS["warning"] - 5 for t in recent_temps):
                profile_result = await self.set_power_profile("high_performance")
                if profile_result["success"]:
                    control_result["actions_taken"].append("Switched to High Performance (thermal normal)")
    
    def _get_thermal_state(self, temperature: float) -> str:
        """Get thermal state based on temperature."""
        if temperature >= TEMP_THRESHOLDS["emergency"]:
            return "emergency"
        elif temperature >= TEMP_THRESHOLDS["critical"]:
            return "critical"
        elif temperature >= TEMP_THRESHOLDS["warning"]:
            return "warning"
        else:
            return "normal"
    
    def _get_current_power_scheme(self) -> Optional[str]:
        """Get current Windows power scheme."""
        if platform.system() != "Windows":
            return None
        
        try:
            result = subprocess.run("powercfg /getactivescheme", shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout
                # Parse output to find GUID
                for profile_name, guid in POWER_SCHEMES.items():
                    if guid.lower() in output.lower():
                        return profile_name
            return None
        except Exception as e:
            logger.error(f"[Sentinel] Failed to get current power scheme: {e}")
            return None
    
    def get_thermal_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent thermal history."""
        return self._thermal_history[-limit:]
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current thermal controller status."""
        return {
            "current_power_scheme": self._current_power_scheme,
            "last_profile_change": self._last_profile_change.isoformat() if self._last_profile_change else None,
            "profile_cooldown_minutes": self._profile_cooldown.total_seconds() / 60,
            "thermal_history_count": len(self._thermal_history),
            "temperature_thresholds": TEMP_THRESHOLDS,
        }
