"""
Plan Cache - Cache command plans to reduce LLM calls.

Stores command -> plan mappings for quick reuse.
Uses hash-based lookup with configurable TTL.
"""

import os
import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CACHE_MAX_SIZE = 500  # Maximum cached plans
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "plan_cache.json"


class PlanCache:
    """
    In-memory cache for command plans with disk persistence.
    
    Reduces LLM API calls by caching successful plans.
    Uses command hash as key, stores plan + metadata.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        logger.info(f"[CACHE] Loaded {len(self._cache)} cached plans")
    
    def _hash_command(self, command: str) -> str:
        """Generate hash for command (case-insensitive, normalized)."""
        # Normalize: lowercase, strip, collapse whitespace
        normalized = " ".join(command.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def get(self, command: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached plan for command.
        
        Returns:
            List of action steps if found and valid, None otherwise
        """
        key = self._hash_command(command)
        
        if key not in self._cache:
            logger.debug(f"[CACHE] Miss: '{command[:50]}...'")
            return None
        
        entry = self._cache[key]
        
        # Check TTL
        if time.time() - entry.get("created_at", 0) > CACHE_TTL_SECONDS:
            logger.debug(f"[CACHE] Expired: '{command[:50]}...'")
            del self._cache[key]
            return None
        
        logger.info(f"[CACHE] Hit: '{command[:50]}...' ({entry.get('hit_count', 0)} hits)")
        
        # Update hit count
        entry["hit_count"] = entry.get("hit_count", 0) + 1
        entry["last_used"] = time.time()
        
        return entry.get("plan")
    
    def put(self, command: str, plan: List[Dict[str, Any]]) -> None:
        """
        Cache a successful plan.
        
        Args:
            command: Original user command
            plan: List of action steps
        """
        if not plan:
            return
        
        key = self._hash_command(command)
        
        self._cache[key] = {
            "command": command,
            "plan": plan,
            "created_at": time.time(),
            "last_used": time.time(),
            "hit_count": 0
        }
        
        # Evict oldest if over limit
        if len(self._cache) > CACHE_MAX_SIZE:
            self._evict_oldest()
        
        logger.info(f"[CACHE] Stored: '{command[:50]}...' ({len(plan)} steps)")
        
        # Persist to disk (async would be better but simpler for now)
        self._save_cache()
    
    def invalidate(self, command: str) -> None:
        """Remove a specific command from cache."""
        key = self._hash_command(command)
        if key in self._cache:
            del self._cache[key]
            logger.info(f"[CACHE] Invalidated: '{command[:50]}...'")
    
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._save_cache()
        logger.info("[CACHE] Cleared all cached plans")
    
    def _evict_oldest(self) -> None:
        """Remove oldest entries to stay under limit."""
        # Sort by last_used, remove oldest 10%
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].get("last_used", 0)
        )
        evict_count = len(sorted_keys) // 10 or 1
        
        for key in sorted_keys[:evict_count]:
            del self._cache[key]
        
        logger.debug(f"[CACHE] Evicted {evict_count} old entries")
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r") as f:
                    self._cache = json.load(f)
        except Exception as e:
            logger.warning(f"[CACHE] Failed to load cache: {e}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"[CACHE] Failed to save cache: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(e.get("hit_count", 0) for e in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": CACHE_MAX_SIZE,
            "total_hits": total_hits,
            "ttl_hours": CACHE_TTL_SECONDS / 3600
        }


# Singleton instance
_plan_cache: Optional[PlanCache] = None


def get_plan_cache() -> PlanCache:
    """Get the singleton PlanCache instance."""
    global _plan_cache
    if _plan_cache is None:
        _plan_cache = PlanCache()
    return _plan_cache
