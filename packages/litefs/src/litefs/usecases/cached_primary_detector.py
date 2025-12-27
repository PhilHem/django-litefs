"""Cached primary detector decorator for LiteFS."""

import time
from typing import Optional

from litefs.usecases.primary_detector import PrimaryDetector


class CachedPrimaryDetector:
    """Decorator that adds TTL-based caching to PrimaryDetector.

    When ttl_seconds is 0 (default), no caching is applied and every call
    to is_primary() delegates directly to the wrapped detector.

    When ttl_seconds > 0, the result of is_primary() is cached for the
    specified duration before the next call to the wrapped detector.
    """

    def __init__(self, wrapped: PrimaryDetector, ttl_seconds: float = 0) -> None:
        """Initialize cached primary detector.

        Args:
            wrapped: The PrimaryDetector to wrap
            ttl_seconds: Cache TTL in seconds. 0 means no caching.
        """
        self._wrapped = wrapped
        self._ttl_seconds = ttl_seconds
        self._cached_value: Optional[bool] = None
        self._cache_time: Optional[float] = None

    def is_primary(self) -> bool:
        """Check if current node is primary, with optional caching.

        Returns:
            True if this node is primary, False if replica
        """
        if self._ttl_seconds <= 0:
            return self._wrapped.is_primary()

        now = time.monotonic()

        if self._cached_value is not None and self._cache_time is not None:
            if now - self._cache_time < self._ttl_seconds:
                return self._cached_value

        self._cached_value = self._wrapped.is_primary()
        self._cache_time = now
        return self._cached_value
