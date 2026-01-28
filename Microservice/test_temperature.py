"""
Test temperature monitoring fix.
"""

import asyncio
import logging
from app.agents.sentinel.hardware_monitor import HardwareMonitor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_temperature():
    """Test temperature monitoring."""
    print("Testing temperature monitoring...")
    
    monitor = HardwareMonitor()
    
    # Get temperature info
    temp_info = await monitor._get_temperature_info()
    
    print(f"Temperature info: {temp_info}")
    
    if temp_info.get("available"):
        print(f"✅ Temperature monitoring available")
        print(f"   Sensors: {temp_info.get('sensors', {})}")
        print(f"   Max temp: {temp_info.get('max_temp')}°C")
    else:
        print(f"❌ Temperature monitoring not available")
        print(f"   Reason: {temp_info.get('reason', 'Unknown')}")
    
    # Get full health report
    health_report = await monitor.get_health_report()
    temp_data = health_report.get("temperature", {})
    print(f"\nFull temperature data from health report: {temp_data}")


if __name__ == "__main__":
    asyncio.run(test_temperature())
