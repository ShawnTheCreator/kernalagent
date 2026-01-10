"""
Test client for the Kernal Agent AI Brain WebSocket API.
Sends a mock intent and frame to verify the pipeline works end-to-end.
"""
import asyncio
import websockets
import base64
import json
import os

# Create a simple test image if it doesn't exist
TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "test_screenshot.png")

def get_test_image() -> str:
    """Load or create a test image and return as Base64."""
    if os.path.exists(TEST_IMAGE_PATH):
        with open(TEST_IMAGE_PATH, "rb") as img:
            return base64.b64encode(img.read()).decode('utf-8')
    else:
        # Create a simple red test image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(TEST_IMAGE_PATH)
        with open(TEST_IMAGE_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')


async def test_brain():
    """Test the WebSocket connection and AI response."""
    uri = "ws://localhost:8000/ws/stream"
    
    print("[TEST] Connecting to Kernal Agent Brain...")
    async with websockets.connect(uri) as websocket:
        
        # Send intent
        print("[TEST] Sending Intent...")
        await websocket.send(json.dumps({
            "type": "intent_update",
            "payload": "Find the File menu and click it."
        }))

        # Send mock frame
        print("[TEST] Sending Mock Frame...")
        await websocket.send(json.dumps({
            "type": "frame",
            "image": get_test_image()
        }))

        # Wait for response
        response = await websocket.recv()
        print(f"[RESPONSE] Brain Responded: {response}")


if __name__ == "__main__":
    asyncio.run(test_brain())
