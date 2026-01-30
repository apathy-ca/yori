"""
In-memory caching with TTL support for YORI proxy

Provides caching for:
- Policy evaluation results
- Upstream API responses (optional)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration"""
    value: Any
    expires_at: datetime
    created_at: datetime


class InMemoryCache:
    """Simple in-memory cache with TTL and size limits"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of entries (default: 1000)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check if expired
        if entry.expires_at <= datetime.now():
            # Remove expired entry
            del self._cache[key]
            self._misses += 1
            return None

        # Cache hit
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self._default_ttl
        now = datetime.now()

        # Check if we need to evict entries
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_oldest()

        self._cache[key] = CacheEntry(
            value=value,
            expires_at=now + timedelta(seconds=ttl),
            created_at=now,
        )

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        """Clear all entries from cache"""
        self._cache.clear()
        logger.info("Cache cleared")

    def clear_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired = [k for k, v in self._cache.items() if v.expires_at <= now]

        for key in expired:
            del self._cache[key]

        if expired:
            logger.debug(f"Cleared {len(expired)} expired cache entries")

        return len(expired)

    def _evict_oldest(self):
        """Evict oldest entry to make room"""
        if not self._cache:
            return

        # Find oldest entry by creation time
        oldest_key = min(self._cache.items(), key=lambda x: x[1].created_at)[0]
        del self._cache[oldest_key]
        self._evictions += 1

        logger.debug(f"Evicted cache entry: {oldest_key}")

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

    def hit_rate(self) -> float:
        """
        Calculate cache hit rate

        Returns:
            Hit rate as percentage (0-100)
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return (self._hits / total) * 100

    def metrics(self) -> dict[str, Any]:
        """
        Get cache metrics

        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": self.hit_rate(),
        }

    def reset_metrics(self):
        """Reset hit/miss counters"""
        self._hits = 0
        self._misses = 0
        self._evictions = 0


def generate_cache_key(data: dict) -> str:
    """
    Generate deterministic cache key from request data

    Args:
        data: Request data dictionary

    Returns:
        SHA256 hash of normalized data
    """
    # Normalize and sort keys for consistency
    normalized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def generate_policy_cache_key(
    client_ip: str,
    request_path: str,
    request_method: str,
) -> str:
    """
    Generate cache key for policy evaluation

    Args:
        client_ip: Client IP address
        request_path: Request path
        request_method: HTTP method

    Returns:
        Cache key string
    """
    return generate_cache_key({
        "client_ip": client_ip,
        "path": request_path,
        "method": request_method,
    })
