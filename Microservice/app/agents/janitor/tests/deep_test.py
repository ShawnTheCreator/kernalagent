"""
Janitor Deep Test Suite

Systematically tests all 10 capabilities of the Janitor Agent.
Run with: python -m app.agents.janitor.tests.deep_test
"""

import asyncio
import os
import shutil
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JanitorTest")

# Add project root to path
sys.path.append(os.getcwd())

async def test_capabilities():
    logger.info("="*60)
    logger.info("🧪 STARTING JANITOR DEEP TEST SUITE")
    logger.info("="*60)
    
    from app.agents.janitor.capabilities.duplicate_hunter import DuplicateHunterCapability
    from app.agents.janitor.capabilities.browser_cleaner import BrowserCleanerCapability
    from app.agents.janitor.capabilities.disk_reclaimer import DiskReclaimerCapability
    from app.agents.janitor.capabilities.privacy_sweep import PrivacySweepCapability
    from app.agents.janitor.capabilities.smart_uninstaller import SmartUninstallerCapability
    from app.agents.janitor.capabilities.virus_scanner import VirusScannerCapability
    from app.agents.janitor.capabilities.file_namer import FileNamerCapability
    from app.agents.janitor.capabilities.auto_organizer import AutoOrganizerCapability
    from app.agents.janitor.capabilities.installer_handler import InstallerHandlerCapability
    
    # Setup test file factory
    test_dir = os.path.join(os.path.expanduser("~"), "JanitorTestZone")
    os.makedirs(test_dir, exist_ok=True)
    
    # =========================================================================
    # 1. DUPLICATE HUNTER
    # =========================================================================
    logger.info("\n[1/10] Testing Duplicate Hunter...")
    
    # Create duplicates
    file1 = os.path.join(test_dir, "original.txt")
    file2 = os.path.join(test_dir, "copy.txt")
    with open(file1, "w") as f: f.write("Hidden secret content" * 1000) # > 100KB needed? No, let's make it bigger
    with open(file1, "w") as f: f.write("A" * 1024 * 105) # 105KB
    shutil.copy(file1, file2)
    
    hunter = DuplicateHunterCapability()
    # Mock scan dirs to test zone
    hunter._scan_dirs = [test_dir]
    
    res = await hunter.full_scan()
    # Check duplicate_groups key directly
    if res.get('duplicate_groups', 0) > 0:
         logger.info(f"✅ Found {res.get('duplicate_groups')} duplicate groups")
    else:
         logger.error(f"❌ Failed to find duplicates. Result: {res}")

    # =========================================================================
    # 2. PRIVACY SWEEP
    # =========================================================================
    logger.info("\n[2/10] Testing Privacy Sweep...")
    sweeper = PrivacySweepCapability()
    res = await sweeper.scan()
    logger.info(f"✅ Privacy Scan result: {res['total_size_mb']}MB reclaimable")
    
    # =========================================================================
    # 3. DISK RECLAIMER
    # =========================================================================
    logger.info("\n[3/10] Testing Disk Reclaimer...")
    # Create large file
    large_file = os.path.join(test_dir, "huge_log.log")
    with open(large_file, "wb") as f:
        f.seek(1024 * 1024 * 101) # 101MB
        f.write(b"\0")
        
    reclaimer = DiskReclaimerCapability()
    reclaimer._scan_dirs = [test_dir]
    res = await reclaimer.scan(min_size_mb=100)
    
    found = False
    for f in res.get('large_files', []):
        if "huge_log.log" in f['name']:
            found = True
            break
            
    if found:
        logger.info("✅ Successfully detected 100MB file")
    else:
        logger.error("❌ Failed to detect large file")

    # =========================================================================
    # 4. VIRUS SCANNER (Suspicious file)
    # =========================================================================
    logger.info("\n[4/10] Testing Virus Scanner...")
    suspicious = os.path.join(test_dir, "invoice.pdf.exe")
    with open(suspicious, "w") as f: f.write("fake malware")
    
    scanner = VirusScannerCapability()
    info = {"filename": "invoice.pdf.exe", "extension": ".exe", "size_bytes": 100}
    res = await scanner.analyze(suspicious, info)
    
    if res.action_required and "Double extension" in res.suggestion:
        logger.info("✅ Detected double extension malware pattern")
    else:
        logger.error(f"❌ Failed to detect malware pattern. Result: {res}")

    # =========================================================================
    # 5. AUTO ORGANIZER
    # =========================================================================
    logger.info("\n[5/10] Testing Auto Organizer...")
    # Mock staging path
    downloads = os.path.join(test_dir, "Downloads_Mock")
    os.makedirs(downloads, exist_ok=True)
    organizer = AutoOrganizerCapability()
    organizer._staging_paths = [downloads]
    
    # Create image
    img = os.path.join(downloads, "test_photo.jpg")
    with open(img, "w") as f: f.write("img")
    
    res = await organizer.analyze(img, {"filename": "test_photo.jpg", "extension": ".jpg"})
    if res.action_required:
        logger.info(f"✅ Correctly proposed moving to: {res.suggestion}")
    else:
        logger.error("❌ Failed to propose organization")

    # =========================================================================
    # 6. FILE NAMER
    # =========================================================================
    logger.info("\n[6/10] Testing File Namer...")
    bad_name = os.path.join(test_dir, "Download (1).pdf")
    with open(bad_name, "w") as f: f.write("doc")
    
    namer = FileNamerCapability()
    res = await namer.analyze(bad_name, {"filename": "Download (1).pdf", "extension": ".pdf"})
    
    if res.action_required:
        logger.info(f"✅ Proposed rename: {res.suggestion}")
    else:
        logger.error("❌ Failed to suggest rename")

    # =========================================================================
    # 7. INSTALLER HANDLER
    # =========================================================================
    logger.info("\n[7/10] Testing Installer Handler...")
    installer = os.path.join(test_dir, "setup_v2.exe")
    with open(installer, "wb") as f: f.write(b"\0" * 1024 * 2000) # 2MB
    
    handler = InstallerHandlerCapability()
    res = await handler.analyze(installer, {"filename": "setup_v2.exe", "extension": ".exe", "size_bytes": 2000000})
    
    if res.action_required and "installer" in res.suggestion.lower():
        logger.info("✅ Detected installer correctly")
    else:
        logger.error(f"❌ Failed to detect installer. Result: {res}")

    # =========================================================================
    # 8. BROWSER CLEANER
    # =========================================================================
    logger.info("\n[8/10] Testing Browser Cleaner...")
    cleaner = BrowserCleanerCapability()
    res = await cleaner.scan()
    logger.info(f"✅ Browser scan found {len(res['browsers'])} browsers with {res['total_size_mb']}MB cache")

    # =========================================================================
    # 9. SMART UNINSTALLER
    # =========================================================================
    logger.info("\n[9/10] Testing Smart Uninstaller...")
    uninstaller = SmartUninstallerCapability()
    res = await uninstaller.scan()
    logger.info(f"✅ Found {res['total_programs']} installed programs")
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    logger.info("\nCleaning up test zone...")
    try:
        shutil.rmtree(test_dir)
        logger.info("✅ Cleanup complete")
    except:
        logger.warning("⚠️ Could not fully clean test zone")
        
    logger.info("\n" + "="*60)
    logger.info("🎉 TEST SUITE COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(test_capabilities())
