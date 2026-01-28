"""
Verify Episodic Memory Timeline

Tests that:
1. Events can be manually logged.
2. Transactions (moves/deletes) automatically appear in the timeline.
3. API endpoints return the timeline.
"""
import sys
import os
import asyncio
import logging
import aiohttp
import time

# Add project root to path
sys.path.append(os.getcwd())

from app.db.memory_bridge import log_event, get_timeline, clear_timeline
from app.agents.janitor.janitor_tools import safe_move

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("TimelineTest")

async def test_timeline():
    print("🧠 TESTING EPISODIC MEMORY TIMELINE")
    print("-" * 40)
    
    user_id = "default_user"
    
    # 1. clear old timeline
    await clear_timeline(user_id)
    print("1. Cleared timeline")
    
    # 2. Log manual event
    await log_event(
        user_id=user_id,
        event_type="chat_user",
        content="Hello world from test script",
        metadata={"source": "test_script"}
    )
    print("2. Logged manual chat event")
    
    # 3. Trigger Transaction (which should auto-log)
    test_dir = os.path.join(os.path.expanduser("~"), "TimelineTestZone")
    os.makedirs(test_dir, exist_ok=True)
    src = os.path.join(test_dir, "test_file.txt")
    dst = os.path.join(test_dir, "moved_file.txt")
    
    with open(src, "w") as f:
        f.write("Timeline test content")
        
    res = await safe_move(src, dst)
    if res.success:
        print(f"3. Performed file move (should trigger transaction log)")
    else:
        print(f"3. ❌ Move failed: {res.error}")
        return

    # Wait for async logging to happen
    await asyncio.sleep(1)
    
    # 4. Fetch Timeline directly
    events = await get_timeline(user_id)
    print(f"\n4. Fetched {len(events)} events from Repo:")
    found_action = False
    for event in events:
        print(f"   [{event['type']}] {event['content']}")
        if event['type'] == 'action_tool' and 'Moved test_file.txt' in event['content']:
            found_action = True
            
    if found_action:
        print("   ✅ SUCCESS: Transaction auto-logged to timeline!")
    else:
        print("   ❌ FAILURE: Transaction NOT found in timeline")
        
    # 5. Test API
    print("\n5. Testing API Endpoint...")
    async with aiohttp.ClientSession() as session:
        try:
            url = "http://127.0.0.1:8000/api/agents/memory/timeline"
            deadline = time.time() + 15
            last_err = None

            while time.time() < deadline:
                try:
                    async with session.get(url) as resp:
                        print(f"   API Status: {resp.status}")
                        data = await resp.json()
                        print(f"   API Data: {data}")
                        if data.get('count') is not None and data.get('count') >= 2:
                            print("   ✅ API Endpoint working")
                        else:
                            print(f"   ❌ API Endpoint returned invalid data: {data}")
                        last_err = None
                        break
                except Exception as attempt_err:
                    last_err = attempt_err
                    await asyncio.sleep(0.5)

            if last_err is not None:
                raise last_err
                    
        except Exception as e:
            print(f"   ❌ API Connection Failed: {e}")

    # Cleanup
    try:
        import shutil
        shutil.rmtree(test_dir)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_timeline())
