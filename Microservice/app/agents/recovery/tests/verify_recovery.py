"""
Recovery Agent Verification Script

Tests the end-to-end "Undo" functionality.
1. Creates a test file
2. Uses Janitor tools to move it (logging transaction)
3. Calls API to undo the last action
4. Verifies file is back
"""

import asyncio
import os
import shutil
import logging
import sys
import aiohttp

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("RecoveryTest")

# Add project root to path
sys.path.append(os.getcwd())

async def test_recovery():
    logger.info("🛡️ STARTING RECOVERY TEST")
    
    test_dir = os.path.join(os.path.expanduser("~"), "RecoveryTestZone")
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Create file
    src = os.path.join(test_dir, "important_doc.txt")
    dst_dir = os.path.join(test_dir, "Archive")
    dst = os.path.join(dst_dir, "important_doc.txt")
    
    with open(src, "w") as f:
        f.write("Very important content")
        
    logger.info(f"1. Created test file: {src}")
    
    # 2. Move file (Using Janitor tools to trigger transaction log)
    from app.agents.janitor.janitor_tools import safe_move
    res = await safe_move(src, dst)
    
    if res.success:
        logger.info(f"2. Moved file to: {dst}")
    else:
        logger.error(f"❌ Move failed: {res.error}")
        return

    # Verify move
    if not os.path.exists(dst) or os.path.exists(src):
        logger.error("❌ Move verification failed")
        return
        
    # 3. Call Undo API
    logger.info("3. Calling /api/agents/recovery/undo...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("http://127.0.0.1:8000/api/agents/recovery/undo") as resp:
                data = await resp.json()
                logger.info(f"   API Response: {data}")
                
                if data.get("success"):
                    logger.info("   ✅ API reported success")
                else:
                    logger.error(f"   ❌ API reported failure: {data}")
                    return
        except Exception as e:
            logger.error(f"   ❌ Connection failed: {e}")
            return

    # 4. Verify Undo
    if os.path.exists(src) and not os.path.exists(dst):
        logger.info("4. ✅ SUCCESS: File restored to original location!")
    else:
        logger.error("4. ❌ FAILURE: File not restored properly")
        logger.info(f"   Src exists: {os.path.exists(src)}")
        logger.info(f"   Dst exists: {os.path.exists(dst)}")

    # Cleanup
    try:
        shutil.rmtree(test_dir)
        # Also clean logs? No, keep for history
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_recovery())
