"""
Mock WebSocket Server for Testing Frontend Live Activity Panel.

This creates a simple WebSocket server on port 8000 that sends
mock action messages periodically to test the frontend dashboard.
"""
import asyncio
import json
import random
from datetime import datetime
import websockets

# Sample actions to broadcast
SAMPLE_ACTIONS = [
    {"action_type": "THINKING", "explanation": "Analyzing the current screen state..."},
    {"action_type": "OBSERVING", "explanation": "Reading window titles and UI elements"},
    {"action_type": "PLANNING", "explanation": "Determining the best approach for the task"},
    {"action_type": "CLICKING", "explanation": "Clicking on the Export button at position (842, 156)"},
    {"action_type": "TYPING", "explanation": "Entering filename: report_2024.pdf"},
    {"action_type": "SCROLLING", "explanation": "Scrolling down to find the save location"},
    {"action_type": "OPENING", "explanation": "Opening File Explorer application"},
    {"action_type": "EXECUTING", "explanation": "Running export workflow automation"},
    {"action_type": "CLICK", "explanation": "Clicking Save button to confirm export"},
    {"action_type": "TYPE", "explanation": "Typing search query into browser"},
    {"action_type": "SCROLL", "explanation": "Scrolling page to view more results"},
    {"action_type": "WAIT", "explanation": "Waiting for page to load..."},
    {"action_type": "ERROR", "explanation": "Failed to locate target element"},
]

# Track connected clients
connected_clients = set()


async def broadcast_actions():
    """Periodically broadcast random actions to all connected clients."""
    while True:
        if connected_clients:
            # Pick a random action
            action = random.choice(SAMPLE_ACTIONS)
            
            # Create the message in the format frontend expects
            message = json.dumps({
                "type": "action",
                "payload": {
                    "explanation": action["explanation"],
                    "action_type": action["action_type"],
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Broadcast to all connected clients
            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            # Remove disconnected clients
            connected_clients.difference_update(disconnected)
            
            print(f"📤 Broadcast: [{action['action_type']}] {action['explanation']}")
        
        # Wait 2-5 seconds between actions
        await asyncio.sleep(random.uniform(2, 5))


async def handle_client(websocket):
    """Handle a WebSocket client connection."""
    connected_clients.add(websocket)
    client_id = id(websocket)
    print(f"✅ Client {client_id} connected! Total clients: {len(connected_clients)}")
    
    try:
        # Keep connection alive and handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"📥 Received from {client_id}: {data.get('type', 'unknown')}")
            except json.JSONDecodeError:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"👋 Client {client_id} disconnected. Total clients: {len(connected_clients)}")


async def main():
    """Start the mock WebSocket server."""
    print("🧪 Mock WebSocket Server for Testing")
    print("=" * 50)
    print("Starting server on ws://localhost:8000/ws/stream")
    print("This will broadcast random actions to test the frontend.\n")
    
    # Start the broadcast task
    broadcast_task = asyncio.create_task(broadcast_actions())
    
    # Start WebSocket server
    async with websockets.serve(handle_client, "localhost", 8000, ping_interval=20):
        print("✅ Server running! Open http://localhost:3000/dashboard to test.\n")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped.")

