"""
Simple in-memory LLM response cache.
Reduces API calls and improves response times for repeated requests.
"""
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.logger import get_logger
from app.core.monitoring import get_monitor

logger = get_logger("core.llm_cache")


class LLMCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize the LLM cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
            max_size: Maximum number of entries to cache (default: 1000)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_size = max_size
        self.monitor = get_monitor()
        logger.info(f"LLM cache initialized with TTL={ttl_seconds}s, max_size={max_size}")

    def _get_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: The prompt text
            model: Model name
            temperature: Temperature setting

        Returns:
            SHA256 hash of the parameters
        """
        key_data = f"{prompt}:{model}:{temperature}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """
        Check if a cache entry has expired.

        Args:
            entry: Cache entry with timestamp

        Returns:
            True if expired
        """
        if "timestamp" not in entry:
            return True
        age = datetime.utcnow() - entry["timestamp"]
        return age > self.ttl

    def _evict_oldest(self):
        """Evict oldest cache entry if at max capacity."""
        if len(self.cache) >= self.max_size:
            # Find oldest entry
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].get("timestamp", datetime.min)
            )
            del self.cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key[:8]}...")

    def get(self, prompt: str, model: str, temperature: float) -> Optional[str]:
        """
        Get cached response if available and not expired.

        Args:
            prompt: The prompt text
            model: Model name
            temperature: Temperature setting

        Returns:
            Cached response or None if not found/expired
        """
        key = self._get_cache_key(prompt, model, temperature)

        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                self.monitor.track_cache_hit()
                logger.debug(f"Cache hit: {key[:8]}...")
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[key]
                logger.debug(f"Cache expired: {key[:8]}...")

        self.monitor.track_cache_miss()
        logger.debug(f"Cache miss: {key[:8]}...")
        return None

    def set(self, prompt: str, model: str, temperature: float, response: str):
        """
        Cache LLM response.

        Args:
            prompt: The prompt text
            model: Model name
            temperature: Temperature setting
            response: The response to cache
        """
        key = self._get_cache_key(prompt, model, temperature)

        # Evict if at capacity
        self._evict_oldest()

        self.cache[key] = {
            "response": response,
            "timestamp": datetime.utcnow()
        }
        logger.debug(f"Cached response: {key[:8]}... (size: {len(self.cache)})")

    def clear(self):
        """Clear all cache entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        expired_count = sum(
            1 for entry in self.cache.values()
            if self._is_expired(entry)
        )

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "expired_entries": expired_count,
            "ttl_seconds": self.ttl.total_seconds()
        }


# Global cache instance
_cache: Optional[LLMCache] = None


def get_cache(ttl_seconds: int = 3600, max_size: int = 1000) -> LLMCache:
    """
    Get the global LLM cache instance.

    Args:
        ttl_seconds: TTL for cache entries (only used on first call)
        max_size: Maximum cache size (only used on first call)

    Returns:
        Global LLMCache instance
    """
    global _cache
    if _cache is None:
        _cache = LLMCache(ttl_seconds=ttl_seconds, max_size=max_size)
    return _cache
