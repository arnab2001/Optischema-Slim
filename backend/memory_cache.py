"""
In-memory TTL cache for OptiSchema Slim.
Stores expensive computation results (schema health, unused index analysis,
AI summaries) so users don't need to rescan on every page load.

Survives across requests but not across server restarts.
"""

import time
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 600):
        """
        Args:
            default_ttl: Default time-to-live in seconds (default 10 minutes)
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None

        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = None):
        """Store a value with optional custom TTL."""
        self._store[key] = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + (ttl or self._default_ttl)
        }

    def get_age(self, key: str) -> Optional[float]:
        """Get how old a cached entry is in seconds. None if not cached."""
        entry = self._store.get(key)
        if entry is None:
            return None
        age = time.time() - entry["created_at"]
        if time.time() > entry["expires_at"]:
            return None
        return age

    def invalidate(self, key: str):
        """Remove a specific key."""
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str):
        """Remove all keys starting with a prefix."""
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._store[k]

    def clear(self):
        """Clear all cached data."""
        self._store.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        total = len(self._store)
        active = sum(1 for e in self._store.values() if now <= e["expires_at"])
        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": total - active
        }


# Singleton instance — shared across all services
# TTL defaults:
#   schema_health: 10 min
#   unused_indexes: 10 min
#   ai_summary: 30 min (more expensive to regenerate)
#   health_scan: 5 min
app_cache = MemoryCache(default_ttl=600)

# Cache key constants
CACHE_SCHEMA_HEALTH = "schema_health"
CACHE_UNUSED_INDEXES = "unused_indexes"
CACHE_AI_SCHEMA_SUMMARY = "ai_schema_summary"
CACHE_HEALTH_SCAN = "health_scan"
CACHE_ANALYSIS_PREFIX = "analysis:"  # per-query, keyed by normalized query text
