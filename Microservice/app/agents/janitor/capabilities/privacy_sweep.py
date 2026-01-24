"""
Privacy Sweep - Clears sensitive data trails and privacy-sensitive files.

Clears:
- Recent documents list
- Temp files
- Clipboard history
- Search history
- Thumbnail cache
- Prefetch files
- Windows event logs (optional)
"""

import os
import shutil
import logging
import subprocess
from datetime import datetime
from typing import Optional

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


class PrivacySweepCapability(BaseCapability):
    """Clears privacy-sensitive data and traces."""
    
    name = "privacy_sweep"
    description = "Clears recent documents, temp files, and privacy traces"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self._local_appdata = os.environ.get("LOCALAPPDATA", "")
        self._appdata = os.environ.get("APPDATA", "")
        self._temp = os.environ.get("TEMP", "")
        
        # Privacy-sensitive locations
        self._privacy_paths = {
            "recent_docs": os.path.join(self._appdata, "Microsoft", "Windows", "Recent"),
            "temp": self._temp,
            "prefetch": "C:\\Windows\\Prefetch",
            "thumbnail_cache": os.path.join(self._local_appdata, "Microsoft", "Windows", "Explorer"),
            "clipboard_history": os.path.join(self._local_appdata, "Microsoft", "Windows", "Clipboard"),
            "search_history": os.path.join(self._local_appdata, "Microsoft", "Windows", "SearchHistory"),
        }
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        This capability doesn't analyze individual files.
        Use sweep() method for privacy cleanup.
        """
        return CapabilityResult(capability=self.name, action_required=False)
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Execute privacy sweep."""
        sweep_type = result.metadata.get("sweep_type", "basic")
        result = await self.sweep(sweep_type == "deep")
        return result.get("success", False)
    
    async def scan(self) -> dict:
        """Scan and report privacy data sizes."""
        results = {}
        total_size = 0
        
        for name, path in self._privacy_paths.items():
            if os.path.exists(path):
                size = self._get_folder_size(path)
                results[name] = {
                    "path": path,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "exists": True,
                }
                total_size += size
            else:
                results[name] = {"exists": False, "size_mb": 0}
        
        return {
            "locations": results,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "reclaimable_mb": round(total_size / (1024 * 1024), 2),
        }
    
    async def sweep(self, deep: bool = False) -> dict:
        """
        Perform privacy sweep.
        
        Args:
            deep: If True, also clears prefetch and event logs
        
        Returns:
            Summary of cleared data
        """
        logger.info(f"[PrivacySweep] Starting {'deep' if deep else 'basic'} sweep...")
        
        cleaned = {}
        total_freed = 0
        
        # Clear recent documents
        recent_path = self._privacy_paths["recent_docs"]
        if os.path.exists(recent_path):
            freed = self._clear_folder(recent_path)
            cleaned["recent_docs"] = {"freed_mb": round(freed / (1024*1024), 2), "success": True}
            total_freed += freed
        
        # Clear temp files
        temp_path = self._privacy_paths["temp"]
        if os.path.exists(temp_path):
            freed = self._clear_folder(temp_path, keep_root=True)
            cleaned["temp"] = {"freed_mb": round(freed / (1024*1024), 2), "success": True}
            total_freed += freed
        
        # Clear thumbnail cache
        thumb_path = self._privacy_paths["thumbnail_cache"]
        if os.path.exists(thumb_path):
            freed = self._clear_thumbcache(thumb_path)
            cleaned["thumbnail_cache"] = {"freed_mb": round(freed / (1024*1024), 2), "success": True}
            total_freed += freed
        
        # Clear clipboard history
        clip_path = self._privacy_paths["clipboard_history"]
        if os.path.exists(clip_path):
            freed = self._clear_folder(clip_path)
            cleaned["clipboard_history"] = {"freed_mb": round(freed / (1024*1024), 2), "success": True}
            total_freed += freed
        
        if deep:
            # Clear prefetch (requires admin)
            try:
                prefetch_path = self._privacy_paths["prefetch"]
                if os.path.exists(prefetch_path):
                    freed = self._clear_folder(prefetch_path, keep_root=True)
                    cleaned["prefetch"] = {"freed_mb": round(freed / (1024*1024), 2), "success": True}
                    total_freed += freed
            except PermissionError:
                cleaned["prefetch"] = {"success": False, "error": "Requires admin"}
            
            # Clear Windows event logs
            try:
                subprocess.run(
                    ["wevtutil", "cl", "Application"],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ["wevtutil", "cl", "System"],
                    capture_output=True, timeout=10
                )
                cleaned["event_logs"] = {"success": True}
            except:
                cleaned["event_logs"] = {"success": False}
        
        logger.info(f"[PrivacySweep] Completed. Freed: {round(total_freed/(1024*1024), 2)} MB")
        
        return {
            "success": True,
            "sweep_type": "deep" if deep else "basic",
            "locations": cleaned,
            "total_freed_mb": round(total_freed / (1024 * 1024), 2),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _clear_folder(self, path: str, keep_root: bool = False) -> int:
        """Clear folder contents, return bytes freed."""
        freed = 0
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isdir(item_path):
                        size = self._get_folder_size(item_path)
                        shutil.rmtree(item_path, ignore_errors=True)
                        freed += size
                    else:
                        size = os.path.getsize(item_path)
                        os.remove(item_path)
                        freed += size
                except:
                    pass
        except:
            pass
        
        return freed
    
    def _clear_thumbcache(self, path: str) -> int:
        """Clear thumbnail cache files."""
        freed = 0
        
        try:
            for item in os.listdir(path):
                if item.startswith("thumbcache_"):
                    item_path = os.path.join(path, item)
                    try:
                        size = os.path.getsize(item_path)
                        os.remove(item_path)
                        freed += size
                    except:
                        pass
        except:
            pass
        
        return freed
    
    def _get_folder_size(self, path: str) -> int:
        """Get total size of a folder."""
        total = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except:
                        pass
        except:
            pass
        return total
