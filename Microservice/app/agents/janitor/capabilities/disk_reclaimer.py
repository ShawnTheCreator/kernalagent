"""
Disk Space Reclaimer - Finds large files hidden in deep folders.

Scans for:
- Files > 500MB buried in subdirectories
- Old game installers
- Forgotten downloads
- Large log files
- Backup files taking up space
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


class DiskReclaimerCapability(BaseCapability):
    """Finds large files that can be deleted to reclaim disk space."""
    
    name = "disk_reclaimer"
    description = "Finds large hidden files to reclaim disk space"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self._min_size_mb = 100  # Files larger than 100MB
        self._scan_depth = 10
        
        # Paths to scan
        self._scan_dirs = [
            self._user_home,
        ]
        
        # Paths to skip
        self._skip_patterns = [
            "Windows",
            "Program Files",
            "Program Files (x86)",
            "$Recycle.Bin",
            "AppData\\Local\\Microsoft",
            ".git",
            "node_modules",
        ]
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Check if this is a large file that could be reclaimed.
        """
        size_bytes = file_info.get("size_bytes", 0)
        size_mb = size_bytes / (1024 * 1024)
        
        if size_mb < self._min_size_mb:
            return CapabilityResult(capability=self.name, action_required=False)
        
        # Check if it's in a deep subdirectory
        depth = file_path.replace(self._user_home, "").count(os.sep)
        
        if depth > 3:  # Buried deep
            return CapabilityResult(
                capability=self.name,
                action_required=True,
                action_type="report_large",
                confidence=0.7,
                suggestion=f"💾 Large file found: {round(size_mb)}MB in deep folder",
                requires_permission=True,
                metadata={
                    "size_mb": round(size_mb, 2),
                    "depth": depth,
                    "path": file_path,
                }
            )
        
        return CapabilityResult(capability=self.name, action_required=False)
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Delete the large file (with user approval)."""
        try:
            from app.agents.janitor.janitor_tools import safe_delete
            delete_result = await safe_delete(file_path, to_recycle=True)
            return delete_result.success
        except Exception as e:
            logger.error(f"[DiskReclaimer] Delete failed: {e}")
            return False
    
    async def scan(self, min_size_mb: int = 100) -> dict:
        """
        Scan for large files across user directories.
        
        Returns list of large files sorted by size.
        """
        logger.info(f"[DiskReclaimer] Scanning for files > {min_size_mb}MB...")
        
        large_files = []
        min_bytes = min_size_mb * 1024 * 1024
        scanned = 0
        
        for scan_dir in self._scan_dirs:
            if not os.path.exists(scan_dir):
                continue
            
            for root, dirs, files in os.walk(scan_dir):
                # Skip protected directories
                if any(skip in root for skip in self._skip_patterns):
                    dirs.clear()  # Don't descend
                    continue
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    scanned += 1
                    
                    try:
                        size = os.path.getsize(filepath)
                        if size >= min_bytes:
                            stat = os.stat(filepath)
                            age_days = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                            
                            large_files.append({
                                "path": filepath,
                                "name": filename,
                                "size_mb": round(size / (1024 * 1024), 2),
                                "age_days": age_days,
                                "extension": Path(filepath).suffix.lower(),
                            })
                    except:
                        pass
        
        # Sort by size (largest first)
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        
        total_reclaimable = sum(f["size_mb"] for f in large_files)
        
        logger.info(f"[DiskReclaimer] Found {len(large_files)} large files")
        
        return {
            "scanned": scanned,
            "large_files": large_files[:50],  # Top 50
            "total_count": len(large_files),
            "total_reclaimable_mb": round(total_reclaimable, 2),
            "total_reclaimable_gb": round(total_reclaimable / 1024, 2),
        }
    
    async def find_old_installers(self, days: int = 30) -> dict:
        """Find old installer files that are likely safe to delete."""
        downloads = os.path.join(self._user_home, "Downloads")
        
        old_installers = []
        threshold = datetime.now() - timedelta(days=days)
        
        if os.path.exists(downloads):
            for filename in os.listdir(downloads):
                filepath = os.path.join(downloads, filename)
                
                if not os.path.isfile(filepath):
                    continue
                
                ext = Path(filepath).suffix.lower()
                if ext not in [".exe", ".msi", ".dmg"]:
                    continue
                
                try:
                    stat = os.stat(filepath)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    
                    if mtime < threshold:
                        old_installers.append({
                            "path": filepath,
                            "name": filename,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "age_days": (datetime.now() - mtime).days,
                        })
                except:
                    pass
        
        total_size = sum(f["size_mb"] for f in old_installers)
        
        return {
            "old_installers": old_installers,
            "count": len(old_installers),
            "total_size_mb": round(total_size, 2),
        }
