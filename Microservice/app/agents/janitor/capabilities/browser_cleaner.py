"""
Browser Deep Clean - Clears browser caches, cookies, and history.

Supports:
- Chrome
- Edge  
- Firefox
- Brave

Can clear: cache, cookies, history, downloads list
"""

import os
import shutil
import logging
from typing import Optional
from datetime import datetime

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


class BrowserCleanerCapability(BaseCapability):
    """Deep cleans browser data."""
    
    name = "browser_cleaner"
    description = "Clears browser caches, cookies, and history"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self._local_appdata = os.environ.get("LOCALAPPDATA", "")
        self._appdata = os.environ.get("APPDATA", "")
        
        # Browser cache paths (Windows)
        self._browser_paths = {
            "chrome": {
                "cache": os.path.join(self._local_appdata, "Google", "Chrome", "User Data", "Default", "Cache"),
                "cookies": os.path.join(self._local_appdata, "Google", "Chrome", "User Data", "Default", "Cookies"),
                "history": os.path.join(self._local_appdata, "Google", "Chrome", "User Data", "Default", "History"),
            },
            "edge": {
                "cache": os.path.join(self._local_appdata, "Microsoft", "Edge", "User Data", "Default", "Cache"),
                "cookies": os.path.join(self._local_appdata, "Microsoft", "Edge", "User Data", "Default", "Cookies"),
                "history": os.path.join(self._local_appdata, "Microsoft", "Edge", "User Data", "Default", "History"),
            },
            "firefox": {
                "cache": os.path.join(self._local_appdata, "Mozilla", "Firefox", "Profiles"),
                # Firefox uses profile folders
            },
            "brave": {
                "cache": os.path.join(self._local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cache"),
                "cookies": os.path.join(self._local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cookies"),
                "history": os.path.join(self._local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "History"),
            },
        }
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        This capability doesn't analyze individual files.
        Use scan() method for browser analysis.
        """
        return CapabilityResult(
            capability=self.name,
            action_required=False,
        )
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Execute browser cleanup."""
        browsers = result.metadata.get("browsers", [])
        clean_type = result.metadata.get("clean_type", "cache")
        
        success = True
        for browser in browsers:
            try:
                if clean_type == "cache":
                    success = await self._clear_cache(browser) and success
                elif clean_type == "all":
                    success = await self._clear_all(browser) and success
            except Exception as e:
                logger.error(f"[BrowserCleaner] Error cleaning {browser}: {e}")
                success = False
        
        return success
    
    async def scan(self) -> dict:
        """
        Scan browser data and return size information.
        """
        results = {}
        total_size = 0
        
        for browser, paths in self._browser_paths.items():
            browser_size = 0
            exists = False
            
            for data_type, path in paths.items():
                if os.path.exists(path):
                    exists = True
                    size = self._get_folder_size(path) if os.path.isdir(path) else os.path.getsize(path)
                    browser_size += size
            
            if exists:
                results[browser] = {
                    "size_mb": round(browser_size / (1024 * 1024), 2),
                    "paths": paths,
                }
                total_size += browser_size
        
        return {
            "browsers": results,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "reclaimable_mb": round(total_size / (1024 * 1024), 2),
        }
    
    async def clean(self, browsers: Optional[list[str]] = None, clean_type: str = "cache") -> dict:
        """
        Clean browser data.
        
        Args:
            browsers: List of browsers to clean (None = all)
            clean_type: "cache", "cookies", "history", or "all"
        
        Returns:
            Summary of cleaned data
        """
        if browsers is None:
            browsers = list(self._browser_paths.keys())
        
        cleaned = {}
        total_freed = 0
        
        for browser in browsers:
            if browser not in self._browser_paths:
                continue
            
            paths = self._browser_paths[browser]
            freed = 0
            
            try:
                if clean_type in ["cache", "all"]:
                    cache_path = paths.get("cache")
                    if cache_path and os.path.exists(cache_path):
                        size = self._get_folder_size(cache_path)
                        shutil.rmtree(cache_path, ignore_errors=True)
                        freed += size
                        logger.info(f"[BrowserCleaner] Cleared {browser} cache")
                
                if clean_type in ["cookies", "all"]:
                    cookies_path = paths.get("cookies")
                    if cookies_path and os.path.exists(cookies_path):
                        try:
                            os.remove(cookies_path)
                            freed += os.path.getsize(cookies_path) if os.path.exists(cookies_path) else 0
                        except:
                            pass
                
                if clean_type in ["history", "all"]:
                    history_path = paths.get("history")
                    if history_path and os.path.exists(history_path):
                        try:
                            os.remove(history_path)
                        except:
                            pass
                
                cleaned[browser] = {
                    "freed_mb": round(freed / (1024 * 1024), 2),
                    "success": True,
                }
                total_freed += freed
                
            except Exception as e:
                cleaned[browser] = {
                    "freed_mb": 0,
                    "success": False,
                    "error": str(e),
                }
        
        logger.info(f"[BrowserCleaner] Total freed: {round(total_freed / (1024*1024), 2)} MB")
        
        return {
            "browsers": cleaned,
            "total_freed_mb": round(total_freed / (1024 * 1024), 2),
        }
    
    async def _clear_cache(self, browser: str) -> bool:
        """Clear cache for a specific browser."""
        paths = self._browser_paths.get(browser, {})
        cache_path = paths.get("cache")
        
        if cache_path and os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path, ignore_errors=True)
                return True
            except:
                return False
        return True
    
    async def _clear_all(self, browser: str) -> bool:
        """Clear all data for a specific browser."""
        result = await self.clean([browser], "all")
        return result.get("browsers", {}).get(browser, {}).get("success", False)
    
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
