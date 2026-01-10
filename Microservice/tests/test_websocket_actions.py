"""
Test script to send mock action messages to the frontend via WebSocket.
This simulates what the backend would send during real agent operation.
"""
import asyncio
import websockets
import json
import random

WS_URL = "ws://localhost:8000/ws/stream"

# Sample actions to send
SAMPLE_ACTIONS = [
    {"action_type": "THINKING", "explanation": "Analyzing the current screen state..."},
    {"action_type": "OBSERVING", "explanation": "Reading window titles and UI elements"},
    {"action_type": "PLANNING", "explanation": "Determining the best click target for export button"},
    {"action_type": "CLICKING", "explanation": "Clicking on the Export button at position (842, 156)"},
    {"action_type": "TYPING", "explanation": "Entering filename: report_2024.pdf"},
    {"action_type": "SCROLLING", "explanation": "Scrolling down to find the save location"},
    {"action_type": "OPENING", "explanation": "Opening File Explorer application"},
    {"action_type": "EXECUTING", "explanation": "Running export workflow automation"},
    {"action_type": "PLANNING", "explanation": "Building action sequence for file save operation"},
    {"action_type": "CLICKING", "explanation": "Clicking Save button to confirm export"},
]


async def send_mock_actions():
    """Connect to WebSocket and send mock action messages."""
    print(f"Connecting to {WS_URL}...")
    
    async with websockets.connect(WS_URL) as ws:
        print("✅ Connected! Sending mock actions every 2-4 seconds...")
        print("   (Press Ctrl+C to stop)\n")
        
        while True:
            # Pick a random action
            action = random.choice(SAMPLE_ACTIONS)
            
            # Create the message in the format frontend expects
            message = {
                "type": "action",
                "payload": {
                    "explanation": action["explanation"],
                    "action_type": action["action_type"]
                }
            }
            
            # Send it
            await ws.send(json.dumps(message))
            print(f"📤 Sent: [{action['action_type']}] {action['explanation']}")
            
            # Wait random time between 2-4 seconds
            delay = random.uniform(2, 4)
            await asyncio.sleep(delay)


if __name__ == "__main__":
    try:
        asyncio.run(send_mock_actions())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped sending mock actions.")
