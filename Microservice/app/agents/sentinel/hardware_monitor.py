"""
Hardware Monitor - Real-time system sensor integration.

Provides hardware telemetry using psutil and WMI:
- CPU usage per core and overall
- RAM usage and available memory  
- GPU/CPU temperatures via WMI
- Process list with resource consumption
- Disk I/O and network activity
"""

import psutil
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import platform

logger = logging.getLogger(__name__)

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logger.warning("WMI not available - temperature monitoring disabled")


class HardwareMonitor:
    """
    Real-time hardware monitoring with cross-platform support.
    
    Windows: Uses psutil + WMI for full telemetry
    Other: Uses psutil only (no temperature data)
    """
    
    def __init__(self):
        self._wmi_client = None
        if WMI_AVAILABLE and platform.system() == "Windows":
            try:
                self._wmi_client = wmi.WMI()
                logger.info("[Sentinel] WMI client initialized for temperature monitoring")
            except Exception as e:
                logger.warning(f"[Sentinel] WMI initialization failed: {e}")
        
        self._last_network_io = None
        self._last_disk_io = None
    
    async def get_health_report(self) -> Dict[str, Any]:
        """
        Complete system health report.
        
        Returns:
            Dict with CPU, RAM, temperature, process, and I/O metrics
        """
        timestamp = datetime.utcnow()
        
        # Core metrics (always available)
        cpu_info = await self._get_cpu_info()
        memory_info = await self._get_memory_info()
        process_info = await self._get_process_info()
        disk_info = await self._get_disk_info()
        network_info = await self._get_network_info()
        
        # Temperature info (Windows only)
        temp_info = await self._get_temperature_info()
        
        # System overview
        system_info = {
            "platform": platform.system(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }
        
        health_report = {
            "timestamp": timestamp.isoformat(),
            "system": system_info,
            "cpu": cpu_info,
            "memory": memory_info,
            "temperature": temp_info,
            "processes": process_info,
            "disk": disk_info,
            "network": network_info,
            "alerts": self._detect_alerts(cpu_info, memory_info, temp_info),
        }
        
        return health_report
    
    async def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU usage and frequency information."""
        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Per-core usage
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # CPU frequency (if available)
        freq = psutil.cpu_freq()
        freq_info = {}
        if freq:
            freq_info = {
                "current_mhz": round(freq.current, 2),
                "min_mhz": round(freq.min, 2) if freq.min else None,
                "max_mhz": round(freq.max, 2) if freq.max else None,
            }
        
        # Load average (Unix-like systems)
        load_avg = {}
        try:
            load_avg = {
                "1min": psutil.getloadavg()[0],
                "5min": psutil.getloadavg()[1], 
                "15min": psutil.getloadavg()[2],
            }
        except (AttributeError, OSError):
            # Windows doesn't have load average
            pass
        
        return {
            "percent_total": round(cpu_percent, 2),
            "percent_per_core": [round(p, 2) for p in cpu_per_core],
            "frequency_mhz": freq_info,
            "load_average": load_avg,
        }
    
    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get RAM and virtual memory information."""
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "virtual": {
                "total_gb": round(virtual.total / (1024**3), 2),
                "available_gb": round(virtual.available / (1024**3), 2),
                "used_gb": round(virtual.used / (1024**3), 2),
                "percent_used": virtual.percent,
                "free_gb": round(virtual.free / (1024**3), 2),
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2),
                "percent_used": swap.percent,
            }
        }
    
    async def _get_process_info(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top processes by CPU and memory usage."""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'memory_info', 'status']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is None:
                    pinfo['cpu_percent'] = 0.0
                if pinfo['memory_percent'] is None:
                    pinfo['memory_percent'] = 0.0
                
                # Convert memory to MB
                memory_mb = 0
                if pinfo['memory_info']:
                    memory_mb = round(pinfo['memory_info'].rss / (1024**2), 2)
                
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "user": pinfo['username'],
                    "cpu_percent": round(pinfo['cpu_percent'], 2),
                    "memory_percent": round(pinfo['memory_percent'], 2),
                    "memory_mb": memory_mb,
                    "status": pinfo['status'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by CPU usage, then by memory usage
        processes.sort(key=lambda x: (x['cpu_percent'], x['memory_percent']), reverse=True)
        
        return processes[:limit]
    
    async def _get_temperature_info(self) -> Dict[str, Any]:
        """Get temperature information (Windows WMI only)."""
        if not self._wmi_client:
            return {"available": False, "reason": "WMI not available"}
        
        try:
            temperatures = {}
            
            # CPU temperature - try multiple WMI classes
            temp_queries = [
                "SELECT * FROM MSAcpi_ThermalZoneTemperature",
                "SELECT * FROM Win32_TemperatureProbe",
                "SELECT * FROM Win32_PerfFormattedData_Counters_ThermalZoneInformation"
            ]
            
            for query in temp_queries:
                try:
                    temps = self._wmi_client.query(query)
                    for temp in temps:
                        if hasattr(temp, 'CurrentTemperature'):
                            # Convert from tenths of kelvin to celsius
                            temp_celsius = (temp.CurrentTemperature - 2732) / 10.0
                            zone_name = getattr(temp, 'InstanceName', getattr(temp, 'Name', f'ThermalZone_{len(temperatures)}'))
                            temperatures[zone_name] = round(temp_celsius, 2)
                        elif hasattr(temp, 'Temperature'):
                            # Direct Celsius value
                            temp_celsius = temp.Temperature
                            zone_name = getattr(temp, 'InstanceName', getattr(temp, 'Name', f'ThermalZone_{len(temperatures)}'))
                            temperatures[zone_name] = round(temp_celsius, 2)
                except Exception as e:
                    logger.debug(f"[Sentinel] Temp query '{query}' failed: {e}")
                    continue
            
            # Try OpenHardwareMonitor if available
            try:
                ohm_temps = self._wmi_client.query("SELECT * FROM Hardware WHERE HardwareType = 'Sensor'")
                for sensor in ohm_temps:
                    if 'Temperature' in getattr(sensor, 'SensorType', ''):
                        name = getattr(sensor, 'Name', 'Unknown')
                        value = getattr(sensor, 'Value', None)
                        if value is not None:
                            temperatures[f"OHM_{name}"] = round(value, 2)
            except Exception as e:
                logger.debug(f"[Sentinel] OpenHardwareMonitor query failed: {e}")
            
            # If no temperatures found, try CoreTemp
            if not temperatures:
                try:
                    core_temps = self._wmi_client.query("SELECT * FROM CoreTemp")
                    for temp in core_temps:
                        for i in range(8):  # Try up to 8 cores
                            core_temp = getattr(temp, f'Core{i}Temp', None)
                            if core_temp and core_temp > 0:
                                temperatures[f"Core{i}"] = round(core_temp, 2)
                except Exception as e:
                    logger.debug(f"[Sentinel] CoreTemp query failed: {e}")
            
            max_temp = None
            if temperatures:
                numeric_temps = [t for t in temperatures.values() if isinstance(t, (int, float)) and t > 0]
                max_temp = max(numeric_temps) if numeric_temps else None
            
            return {
                "available": len(temperatures) > 0,
                "sensors": temperatures,
                "max_temp": max_temp,
                "fan_status": "N/A"  # Could be enhanced with fan queries
            }
            
        except Exception as e:
            logger.warning(f"[Sentinel] Temperature monitoring failed: {e}")
            return {"available": False, "reason": str(e)}
    
    async def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage and I/O statistics."""
        disk_usage = {}
        disk_io = psutil.disk_io_counters()
        
        # Get disk usage for all mounted drives
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    drive_letter = partition.device.replace('\\', '').replace(':', '')
                    disk_usage[drive_letter] = {
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent_used": round((usage.used / usage.total) * 100, 2),
                        "filesystem": partition.fstype,
                        "mountpoint": partition.mountpoint
                    }
                except Exception as e:
                    logger.debug(f"[Sentinel] Failed to get usage for {partition.device}: {e}")
        except Exception as e:
            logger.warning(f"[Sentinel] Disk usage query failed: {e}")
        
        # I/O statistics
        io_stats = {}
        if disk_io:
            # Calculate rates if we have previous data
            read_rate = 0
            write_rate = 0
            
            if self._last_disk_io:
                time_delta = 1.0  # Assume 1 second interval
                read_rate = (disk_io.read_bytes - self._last_disk_io.read_bytes) / time_delta
                write_rate = (disk_io.write_bytes - self._last_disk_io.write_bytes) / time_delta
            
            self._last_disk_io = disk_io
            
            io_stats = {
                "available": True,
                "read_bytes_mb": round(disk_io.read_bytes / (1024**2), 2),
                "write_bytes_mb": round(disk_io.write_bytes / (1024**2), 2),
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_rate_mbps": round(read_rate / (1024**2), 2),
                "write_rate_mbps": round(write_rate / (1024**2), 2),
            }
        else:
            io_stats = {"available": False}
        
        return {
            "usage": disk_usage,
            "io": io_stats
        }
    
    async def _get_network_info(self) -> Dict[str, Any]:
        """Get network I/O statistics."""
        net_io = psutil.net_io_counters()
        
        if not net_io:
            return {"available": False}
        
        # Calculate rates if we have previous data
        sent_rate = 0
        recv_rate = 0
        
        if self._last_network_io:
            time_delta = 1.0  # Assume 1 second interval
            sent_rate = (net_io.bytes_sent - self._last_network_io.bytes_sent) / time_delta
            recv_rate = (net_io.bytes_recv - self._last_network_io.bytes_recv) / time_delta
        
        self._last_network_io = net_io
        
        # Get network interfaces info
        interfaces = {}
        try:
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            for name, addrs in net_if_addrs.items():
                stats = net_if_stats.get(name)
                interfaces[name] = {
                    "is_up": stats.isup if stats else False,
                    "speed": stats.speed if stats else 0,
                    "mtu": stats.mtu if stats else 0,
                    "addresses": [addr.address for addr in addrs[:2]]  # First 2 addresses
                }
        except Exception as e:
            logger.debug(f"[Sentinel] Network interfaces query failed: {e}")
        
        return {
            "available": True,
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
            "bytes_sent_total": round(net_io.bytes_sent / (1024**3), 2),  # GB
            "bytes_recv_total": round(net_io.bytes_recv / (1024**3), 2),  # GB
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "bytes_sent_per_sec": round(sent_rate, 0),  # bytes/sec
            "bytes_recv_per_sec": round(recv_rate, 0),  # bytes/sec
            "sent_rate_mbps": round(sent_rate / (1024**2), 2),
            "recv_rate_mbps": round(recv_rate / (1024**2), 2),
            "interfaces": interfaces
        }
    
    def _detect_alerts(self, cpu_info: Dict, memory_info: Dict, temp_info: Dict) -> List[Dict[str, Any]]:
        """Detect system alerts based on thresholds."""
        alerts = []
        
        # CPU alerts
        cpu_percent = cpu_info.get("percent_total", 0)
        if cpu_percent > 90:
            alerts.append({
                "type": "cpu_high",
                "severity": "critical" if cpu_percent > 95 else "warning",
                "message": f"CPU usage at {cpu_percent}%",
                "threshold": 90,
                "current_value": cpu_percent,
            })
        
        # Memory alerts
        memory_percent = memory_info.get("virtual", {}).get("percent_used", 0)
        if memory_percent > 90:
            alerts.append({
                "type": "memory_high",
                "severity": "critical" if memory_percent > 95 else "warning", 
                "message": f"Memory usage at {memory_percent}%",
                "threshold": 90,
                "current_value": memory_percent,
            })
        
        # Temperature alerts
        if temp_info.get("available") and temp_info.get("max_temp"):
            max_temp = temp_info["max_temp"]
            # Ensure max_temp is numeric before comparison
            if isinstance(max_temp, (int, float)) and max_temp > 85:
                alerts.append({
                    "type": "temperature_high",
                    "severity": "critical" if max_temp > 90 else "warning",
                    "message": f"Temperature at {max_temp}°C",
                    "threshold": 85,
                    "current_value": max_temp,
                })
        
        return alerts
    
    async def get_process_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find process by name (case-insensitive)."""
        name_lower = name.lower()
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == name_lower:
                    return {
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'] or 0.0,
                        "memory_percent": proc.info['memory_percent'] or 0.0,
                        "status": proc.info['status'],
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return None
    
    async def get_high_resource_processes(self, cpu_threshold: float = 5.0, memory_threshold: float = 5.0) -> List[Dict[str, Any]]:
        """Get processes exceeding resource thresholds."""
        high_usage = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                cpu = proc.info['cpu_percent'] or 0.0
                memory = proc.info['memory_percent'] or 0.0
                
                if cpu > cpu_threshold or memory > memory_threshold:
                    high_usage.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": cpu,
                        "memory_percent": memory,
                        "status": proc.info['status'],
                        "reason": "cpu" if cpu > cpu_threshold else "memory",
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return high_usage
