"""
API Retry Utilities

Provides exponential backoff retry logic for vision API calls.
Handles 429 (rate limit) and 503 (overload) errors gracefully.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 2.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds


class RetryableError(Exception):
    """Exception that indicates the operation should be retried."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


def is_retryable_error(error: Exception) -> tuple[bool, Optional[float]]:
    """
    Check if an error is retryable (429/503).
    
    Returns:
        (is_retryable, retry_delay_seconds)
    """
    error_str = str(error)
    
    # Rate limit error (429)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
        # Try to extract retry delay from error message
        if "retry in" in error_str.lower():
            try:
                import re
                match = re.search(r'retry in (\d+\.?\d*)', error_str.lower())
                if match:
                    return (True, float(match.group(1)))
            except:
                pass
        return (True, None)
    
    # Server overload (503)
    if "503" in error_str or "UNAVAILABLE" in error_str:
        return (True, None)
    
    # Server error (500)
    if "500" in error_str or "INTERNAL" in error_str:
        return (True, None)
    
    return (False, None)


async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    **kwargs
) -> T:
    """
    Execute a function with exponential backoff retry.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        **kwargs: Keyword arguments for func
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"[RETRY] Succeeded on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_error = e
            is_retryable, suggested_delay = is_retryable_error(e)
            
            if not is_retryable or attempt >= max_retries:
                logger.error(f"[RETRY] Failed after {attempt + 1} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Use suggested delay if available and larger
            if suggested_delay and suggested_delay > delay:
                delay = min(suggested_delay, max_delay)
            
            logger.warning(f"[RETRY] Attempt {attempt + 1} failed: {type(e).__name__}. Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)
    
    raise last_error


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY
):
    """
    Decorator for adding retry logic to async functions.
    
    Usage:
        @with_retry(max_retries=3)
        async def my_api_call():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                **kwargs
            )
        return wrapper
    return decorator
