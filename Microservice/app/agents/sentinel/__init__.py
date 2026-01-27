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
"""

from .sentinel_agent import SentinelAgent

__all__ = ["SentinelAgent"]
