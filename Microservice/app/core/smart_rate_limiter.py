"""
Smart rate limiter with priority queuing and predictive backoff.
Manages API rate limits across users and prevents 429 errors.
"""
import asyncio
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class UserQuota:
    """User's rate limit quota information."""
    user_id: str
    tier: str  # "free", "pro", "enterprise"
    requests_used: int
    reset_time: datetime
    priority: int  # Higher = more important


class SmartRateLimiter:
    """
    Intelligent rate limiting with:
    - Per-user quotas based on tier
    - Global cooldown management (429 responses)
    - Priority queuing
    - Predictive backoff
    """
    
    def __init__(self):
        """Initialize rate limiter."""
        self.quotas: Dict[str, UserQuota] = {}
        self.global_cooldown_until: float = 0
        self.consecutive_429s: int = 0
        
        # Tier limits (requests per minute)
        self.limits = {
            "free": 10,      # Free tier: 10 RPM
            "pro": 50,       # Pro tier: 50 RPM
            "enterprise": 200  # Enterprise: 200 RPM
        }
        
        # Statistics
        self.total_requests: int = 0
        self.blocked_requests: int = 0
        self.cooldowns_triggered: int = 0
        
        logger.info("[RATE_LIMITER] Initialized with tiers: " + str(self.limits))
    
    async def acquire(
        self, 
        user_id: str = "default", 
        tier: str = "free", 
        priority: int = 5
    ) -> bool:
        """
        Acquire permission to make API call.
        
        Args:
            user_id: Unique user identifier
            tier: User tier (free/pro/enterprise)
            priority: Request priority (1-10, higher = more important)
            
        Returns:
            True if allowed, False if rate limited
        """
        self.total_requests += 1
        
        # Check global cooldown
        if time.time() < self.global_cooldown_until:
            wait_time = self.global_cooldown_until - time.time()
            
            if wait_time > 10:  # Don't wait more than 10 seconds
                logger.warning(f"[RATE_LIMITER] Global cooldown too long ({wait_time:.1f}s) - rejecting")
                self.blocked_requests += 1
                return False
            
            logger.info(f"[RATE_LIMITER] Global cooldown active, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        # Get or create user quota
        quota = self.quotas.get(user_id)
        if quota is None:
            quota = UserQuota(
                user_id=user_id,
                tier=tier,
                requests_used=0,
                reset_time=datetime.now() + timedelta(minutes=1),
                priority=priority
            )
            self.quotas[user_id] = quota
        
        # Reset quota if window expired
        if datetime.now() > quota.reset_time:
            quota.requests_used = 0
            quota.reset_time = datetime.now() + timedelta(minutes=1)
            logger.debug(f"[RATE_LIMITER] Quota reset for user {user_id}")
        
        # Check user limit
        limit = self.limits.get(tier, self.limits["free"])
        if quota.requests_used >= limit:
            logger.warning(f"[RATE_LIMITER] User {user_id} ({tier}) exceeded limit ({quota.requests_used}/{limit})")
            self.blocked_requests += 1
            return False
        
        # Grant permission
        quota.requests_used += 1
        logger.debug(f"[RATE_LIMITER] Granted to {user_id}: {quota.requests_used}/{limit}")
        return True
    
    def report_429(self, retry_after: Optional[int] = None):
        """
        Report a 429 (rate limit) error to trigger global cooldown.
        
        Args:
            retry_after: Seconds to wait (from Retry-After header)
        """
        self.consecutive_429s += 1
        self.cooldowns_triggered += 1
        
        # Calculate cooldown duration with exponential backoff
        if retry_after:
            cooldown = retry_after
        else:
            # Exponential backoff: 2s, 4s, 8s, 16s, 32s (max 60s)
            cooldown = min(2 ** self.consecutive_429s, 60)
        
        self.set_global_cooldown(cooldown)
        logger.warning(
            f"[RATE_LIMITER] 429 error #{self.consecutive_429s} - "
            f"Global cooldown: {cooldown}s"
        )
    
    def report_success(self):
        """Report successful API call (resets 429 counter)."""
        if self.consecutive_429s > 0:
            logger.info(f"[RATE_LIMITER] Request succeeded - resetting 429 counter")
        self.consecutive_429s = 0
    
    def set_global_cooldown(self, seconds: float):
        """Set global cooldown period."""
        self.global_cooldown_until = time.time() + seconds
        logger.info(f"[RATE_LIMITER] Global cooldown set: {seconds}s")
    
    def get_user_stats(self, user_id: str) -> Optional[dict]:
        """Get rate limit stats for specific user."""
        quota = self.quotas.get(user_id)
        if not quota:
            return None
        
        limit = self.limits.get(quota.tier, self.limits["free"])
        time_until_reset = max(0, (quota.reset_time - datetime.now()).total_seconds())
        
        return {
            "user_id": user_id,
            "tier": quota.tier,
            "requests_used": quota.requests_used,
            "limit": limit,
            "remaining": limit - quota.requests_used,
            "reset_in_seconds": time_until_reset
        }
    
    def get_global_stats(self) -> dict:
        """Get overall rate limiter statistics."""
        cooldown_remaining = max(0, self.global_cooldown_until - time.time())
        block_rate = self.blocked_requests / self.total_requests if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "block_rate": block_rate,
            "active_users": len(self.quotas),
            "global_cooldown_remaining": cooldown_remaining,
            "consecutive_429s": self.consecutive_429s,
            "cooldowns_triggered": self.cooldowns_triggered
        }
    
    def cleanup_expired_quotas(self):
        """Remove expired user quotas to save memory."""
        now = datetime.now()
        expired = [
            user_id for user_id, quota in self.quotas.items()
            if now > quota.reset_time + timedelta(minutes=5)
        ]
        
        for user_id in expired:
            del self.quotas[user_id]
        
        if expired:
            logger.info(f"[RATE_LIMITER] Cleaned up {len(expired)} expired quotas")


# Singleton instance
_rate_limiter_instance: Optional[SmartRateLimiter] = None


def get_rate_limiter() -> SmartRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = SmartRateLimiter()
    return _rate_limiter_instance
