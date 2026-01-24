"""
Duplicate File Hunter - Finds duplicate files by content hash.

Scans user directories, computes file hashes, identifies duplicates,
and suggests which copies to delete to reclaim disk space.
"""

import os
import hashlib
import logging
from collections import defaultdict
from typing import Optional
from pathlib import Path

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


class DuplicateHunterCapability(BaseCapability):
    """Finds and reports duplicate files."""
    
    name = "duplicate_hunter"
    description = "Scans for duplicate files and suggests cleanup"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self._scan_dirs = [
            os.path.join(self._user_home, "Downloads"),
            os.path.join(self._user_home, "Documents"),
            os.path.join(self._user_home, "Pictures"),
            os.path.join(self._user_home, "Desktop"),
        ]
        self._min_size = 1024 * 100  # 100KB minimum
        self._cache: dict[str, list[str]] = {}  # hash -> list of paths
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Check if this file is a duplicate of an existing file.
        """
        size_bytes = file_info.get("size_bytes", 0)
        
        # Skip small files
        if size_bytes < self._min_size:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Compute hash
        file_hash = self._quick_hash(file_path)
        if not file_hash:
            return CapabilityResult(capability=self.name, action_required=False)
        
        # Check if we've seen this hash before
        if file_hash in self._cache:
            existing = self._cache[file_hash]
            # Verify files still exist
            existing = [p for p in existing if os.path.exists(p)]
            
            if existing and file_path not in existing:
                self._cache[file_hash].append(file_path)
                
                return CapabilityResult(
                    capability=self.name,
                    action_required=True,
                    action_type="report_duplicate",
                    confidence=0.95,
                    suggestion=f"🔄 Duplicate found: already exists at {os.path.basename(existing[0])}",
                    requires_permission=True,
                    metadata={
                        "duplicate_of": existing[0],
                        "all_copies": existing + [file_path],
                        "hash": file_hash,
                        "size_bytes": size_bytes,
                        "space_reclaimable": size_bytes,
                    }
                )
        else:
            self._cache[file_hash] = [file_path]
        
        return CapabilityResult(
            capability=self.name,
            action_required=False,
        )
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Handle duplicate - user has approved deletion."""
        if result.action_type == "report_duplicate":
            try:
                # Move to trash instead of permanent delete
                from app.agents.janitor.janitor_tools import safe_delete
                delete_result = await safe_delete(file_path, to_recycle=True)
                
                if delete_result.success:
                    logger.info(f"[DuplicateHunter] Removed duplicate: {file_path}")
                    return True
                else:
                    logger.warning(f"[DuplicateHunter] Failed: {delete_result.error}")
                    return False
            except Exception as e:
                logger.error(f"[DuplicateHunter] Error: {e}")
                return False
        
        return True
    
    def _quick_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """Compute MD5 hash of file (fast, good enough for duplicates)."""
        try:
            md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read first and last chunks for speed
                first_chunk = f.read(chunk_size)
                md5.update(first_chunk)
                
                # Seek to end
                f.seek(-min(chunk_size, os.path.getsize(file_path)), 2)
                last_chunk = f.read(chunk_size)
                md5.update(last_chunk)
                
            return md5.hexdigest()
        except Exception:
            return None
    
    async def full_scan(self) -> dict:
        """
        Perform a full duplicate scan across all directories.
        
        Returns summary of duplicates found.
        """
        logger.info("[DuplicateHunter] Starting full scan...")
        
        hash_map: dict[str, list[str]] = defaultdict(list)
        scanned = 0
        
        for scan_dir in self._scan_dirs:
            if not os.path.exists(scan_dir):
                continue
            
            for root, _, files in os.walk(scan_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    try:
                        size = os.path.getsize(filepath)
                        if size < self._min_size:
                            continue
                        
                        file_hash = self._quick_hash(filepath)
                        if file_hash:
                            hash_map[file_hash].append(filepath)
                            scanned += 1
                    except:
                        pass
        
        # Find duplicates
        duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
        
        total_reclaimable = 0
        duplicate_groups = []
        
        for hash_val, paths in duplicates.items():
            try:
                size = os.path.getsize(paths[0])
                reclaimable = size * (len(paths) - 1)
                total_reclaimable += reclaimable
                
                duplicate_groups.append({
                    "hash": hash_val,
                    "files": paths,
                    "size_each": size,
                    "reclaimable": reclaimable,
                })
            except:
                pass
        
        # Update cache
        self._cache = hash_map
        
        logger.info(f"[DuplicateHunter] Found {len(duplicate_groups)} duplicate groups")
        
        return {
            "scanned": scanned,
            "duplicate_groups": len(duplicate_groups),
            "total_reclaimable_mb": round(total_reclaimable / (1024 * 1024), 2),
            "duplicates": duplicate_groups[:20],  # Limit to top 20
        }
