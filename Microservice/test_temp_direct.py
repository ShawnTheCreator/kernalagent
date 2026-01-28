"""
Direct test of temperature fix without server restart.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.sentinel.hardware_monitor import HardwareMonitor
import asyncio

async def test():
    print("Testing temperature fix directly...")
    
    monitor = HardwareMonitor()
    
    # Test the conversion directly
    raw_temp = 298
    print(f"Testing with raw_temp = {raw_temp}")
    
    if 200 <= raw_temp <= 400:  # Likely in Kelvin
        temp_celsius = raw_temp - 273.15
        print(f"✓ Should convert from Kelvin: {raw_temp}K -> {temp_celsius}°C")
    elif 2000 <= raw_temp <= 4000:  # Likely in tenths of Kelvin
        temp_celsius = (raw_temp - 2732) / 10.0
        print(f"✓ Should convert from tenths of Kelvin: {raw_temp} -> {temp_celsius}°C")
    else:
        print(f"✗ Raw temp {raw_temp} doesn't match expected ranges")
    
    # Now test the actual function
    print("\nTesting actual _get_temperature_info function...")
    temp_info = await monitor._get_temperature_info()
    print(f"Actual temperature info: {temp_info}")
    
    # Check if the conversion worked
    if temp_info.get("max_temp") == 298:
        print("❌ Still showing 298°C - fix not working")
        print("   The conversion logic is not being executed!")
    elif temp_info.get("max_temp") and temp_info.get("max_temp") < 100:
        print(f"✅ Fixed! Temperature: {temp_info.get('max_temp')}°C")
    else:
        print(f"⚠️ Unexpected temperature: {temp_info.get('max_temp')}")
    
    # Let's check what the actual code looks like
    print("\nChecking the actual code in hardware_monitor.py...")
    with open("app/agents/sentinel/hardware_monitor.py", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines[200:230], 200):
            if "raw_temp" in line or "temp_celsius" in line:
                print(f"Line {i+200}: {line.strip()}")

if __name__ == "__main__":
    asyncio.run(test())
