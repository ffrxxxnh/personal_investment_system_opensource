# Connector Utilities
# src/data_manager/connectors/utils.py

"""
Utility classes for connector implementations.

Provides rate limiting, caching, and retry logic to ensure reliable
API interactions and respect provider rate limits.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API calls.

    Tracks call frequency and blocks when limits are exceeded to prevent
    API rate limit errors.

    Example:
        limiter = RateLimiter(calls_per_minute=60, calls_per_second=1.0)

        for item in items:
            limiter.wait()  # Blocks if rate limit would be exceeded
            response = api.call(item)

    Attributes:
        calls_per_minute: Maximum calls allowed per minute
        min_interval: Minimum seconds between calls
        last_call_time: Timestamp of last API call
        call_times: List of recent call timestamps
    """

    def __init__(
        self,
        calls_per_minute: int = 60,
        calls_per_second: float = 1.0
    ):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls per minute (default 60)
            calls_per_second: Minimum seconds between calls (default 1.0)
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = max(1.0 / calls_per_second, 60.0 / calls_per_minute)
        self.last_call_time: Optional[float] = None
        self.call_times: list = []

    def wait(self) -> float:
        """
        Block until it's safe to make another API call.

        Returns:
            Actual wait time in seconds (0 if no wait needed)
        """
        now = time.time()
        total_wait = 0.0

        # Clean old call times (older than 1 minute)
        self.call_times = [t for t in self.call_times if now - t < 60]

        # Check per-minute limit
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s (minute limit)")
                time.sleep(sleep_time)
                total_wait += sleep_time
                now = time.time()

        # Check per-call interval
        if self.last_call_time:
            elapsed = now - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s (interval)")
                time.sleep(sleep_time)
                total_wait += sleep_time

        self.last_call_time = time.time()
        self.call_times.append(self.last_call_time)

        return total_wait

    def reset(self) -> None:
        """Reset rate limiter state."""
        self.last_call_time = None
        self.call_times = []


class ResponseCache:
    """
    Simple in-memory cache for API responses.

    Reduces API calls by caching responses with configurable TTL.
    Useful for data that doesn't change frequently (holdings, prices).

    Example:
        cache = ResponseCache(ttl_seconds=300)  # 5 minute TTL

        # Check cache first
        cached = cache.get("price_AAPL")
        if cached:
            return cached

        # Fetch and cache
        price = api.get_price("AAPL")
        cache.set("price_AAPL", price)
        return price

    Attributes:
        ttl: Time-to-live as timedelta
        _cache: Internal cache storage
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live in seconds (default 5 minutes)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}  # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl_override: Optional[int] = None) -> None:
        """
        Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_override: Optional TTL override in seconds
        """
        ttl = timedelta(seconds=ttl_override) if ttl_override else self.ttl
        expiry = datetime.now() + ttl
        self._cache[key] = (value, expiry)

    def invalidate(self, key: str) -> bool:
        """
        Remove specific key from cache.

        Args:
            key: Cache key to invalidate

        Returns:
            True if key was found and removed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        Remove all keys starting with prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of keys removed
        """
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    def clear(self) -> int:
        """
        Clear all cached values.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def make_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            MD5 hash string as cache key
        """
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats:
            - entries: Number of cached entries
            - expired: Number of expired entries (not yet cleaned)
        """
        now = datetime.now()
        expired_count = sum(1 for _, (_, expiry) in self._cache.items() if expiry <= now)
        return {
            "entries": len(self._cache),
            "expired": expired_count,
            "valid": len(self._cache) - expired_count,
        }


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator for retrying failed API calls with exponential backoff.

    Automatically retries function calls that raise specified exceptions,
    with exponentially increasing delays between retries.

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(RateLimitError, NetworkError))
        def fetch_data():
            return api.get_data()

    Args:
        max_retries: Maximum number of retries (default 3)
        initial_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay in seconds (default 60.0)
        exponential_base: Multiplier for delay on each retry (default 2.0)
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback(exception, attempt) called before each retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Call retry callback if provided
                        if on_retry:
                            on_retry(e, attempt + 1)

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed: {e}")

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def sanitize_api_key(key: Optional[str], visible_chars: int = 4) -> str:
    """
    Sanitize API key for logging (show only first/last chars).

    Args:
        key: API key to sanitize
        visible_chars: Number of chars to show at start and end

    Returns:
        Sanitized string like "abc1...xyz9"
    """
    if not key:
        return "<not set>"
    if len(key) <= visible_chars * 2:
        return "*" * len(key)
    return f"{key[:visible_chars]}...{key[-visible_chars:]}"


def generate_source_id(
    source: str,
    transaction_id: Optional[str] = None,
    date: Optional[datetime] = None,
    symbol: Optional[str] = None,
    amount: Optional[float] = None
) -> str:
    """
    Generate a unique source ID for deduplication.

    If transaction_id is provided from the source, uses that.
    Otherwise generates a hash from date, symbol, and amount.

    Args:
        source: Source identifier (e.g., "binance", "schwab")
        transaction_id: External transaction ID from source (preferred)
        date: Transaction date (fallback)
        symbol: Transaction symbol (fallback)
        amount: Transaction amount (fallback)

    Returns:
        Unique source ID string
    """
    if transaction_id:
        return f"{source}_{transaction_id}"

    # Generate hash from available fields
    components = [source]
    if date:
        components.append(date.isoformat())
    if symbol:
        components.append(symbol)
    if amount is not None:
        components.append(f"{amount:.6f}")

    data = "|".join(components)
    hash_value = hashlib.sha256(data.encode()).hexdigest()[:16]
    return f"{source}_{hash_value}"
