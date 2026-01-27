"""
Test client for Sentinel WebSocket alerts.

Run this to test Sentinel daemon alerts in real-time.
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sentinel_test_client():
    """Test client for Sentinel WebSocket."""
    uri = "ws://localhost:8000/ws/sentinel?user_id=test_user"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to Sentinel WebSocket")
            
            # Send a test message
            await websocket.send(json.dumps({
                "type": "update_profile",
                "profile": {
                    "work_hours": [9, 17],
                    "gaming_mode": False,
                    "notifications": True
                }
            }))
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                
                msg_type = data.get("type")
                
                if msg_type == "sentinel_alert":
                    alert = data
                    logger.info(f"🚨 ALERT [{alert['severity'].upper()}]: {alert['message']}")
                    logger.info(f"   Current: {alert['current_value']}, Threshold: {alert['threshold']}")
                    logger.info(f"   Suggestions: {', '.join(alert['suggestions'])}")
                    
                    # Simulate user response
                    if alert['type'] in ['cpu', 'memory']:
                        response = {
                            "type": "sentinel_action",
                            "alert_id": alert['id'],
                            "action": "ignore",
                            "approved": True
                        }
                        await websocket.send(json.dumps(response))
                        logger.info(f"   Sent response: {response['action']}")
                
                elif msg_type == "sentinel_health_score":
                    score = data['score']
                    logger.info(f"💚 System Health Score: {score}/100")
                    
                    if score < 50:
                        logger.warning("   System health is POOR")
                    elif score < 75:
                        logger.info("   System health is FAIR")
                    else:
                        logger.info("   System health is GOOD")
                
                elif msg_type == "sentinel_status":
                    logger.info(f"📊 Status: {data}")
                
                elif msg_type == "sentinel_cleanup_completed":
                    logger.info(f"🧹 Cleanup completed: {data['actions_executed']} actions")
                
                elif msg_type == "sentinel_maintenance_completed":
                    logger.info(f"🔧 Maintenance completed: {data['task']}")
                
                else:
                    logger.info(f"📨 Received: {msg_type}")
    
    except websockets.exceptions.ConnectionRefused:
        logger.error("Connection refused. Is the server running?")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    print("Sentinel WebSocket Test Client")
    print("=" * 40)
    print("Make sure the server is running on localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    asyncio.run(sentinel_test_client())
