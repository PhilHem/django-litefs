"""Unit tests for CachedPrimaryDetector use case."""

import time
from unittest.mock import Mock

import pytest

from litefs.usecases.cached_primary_detector import CachedPrimaryDetector
from litefs.usecases.primary_detector import PrimaryDetector


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestCachedPrimaryDetector:
    """Test CachedPrimaryDetector decorator."""

    def test_no_caching_delegates_directly(self) -> None:
        """Test that with ttl=0, every call delegates to wrapped detector."""
        wrapped = Mock(spec=PrimaryDetector)
        wrapped.is_primary.side_effect = [True, False, True]

        cached = CachedPrimaryDetector(wrapped, ttl_seconds=0)

        assert cached.is_primary() is True
        assert cached.is_primary() is False
        assert cached.is_primary() is True
        assert wrapped.is_primary.call_count == 3

    def test_caching_returns_cached_value(self) -> None:
        """Test that with TTL > 0, result is cached and wrapped is called once."""
        wrapped = Mock(spec=PrimaryDetector)
        wrapped.is_primary.return_value = True

        cached = CachedPrimaryDetector(wrapped, ttl_seconds=10.0)

        assert cached.is_primary() is True
        assert cached.is_primary() is True
        assert cached.is_primary() is True
        assert wrapped.is_primary.call_count == 1

    def test_cache_expires_after_ttl(self) -> None:
        """Test that cache expires after TTL seconds and wrapped is called again."""
        wrapped = Mock(spec=PrimaryDetector)
        wrapped.is_primary.side_effect = [True, False]

        cached = CachedPrimaryDetector(wrapped, ttl_seconds=0.05)

        assert cached.is_primary() is True
        assert wrapped.is_primary.call_count == 1

        # Wait for cache to expire
        time.sleep(0.06)

        assert cached.is_primary() is False
        assert wrapped.is_primary.call_count == 2

    def test_default_ttl_is_zero(self) -> None:
        """Test that default TTL is 0 (no caching)."""
        wrapped = Mock(spec=PrimaryDetector)
        wrapped.is_primary.side_effect = [True, False]

        cached = CachedPrimaryDetector(wrapped)

        assert cached.is_primary() is True
        assert cached.is_primary() is False
        assert wrapped.is_primary.call_count == 2

    def test_caches_false_value(self) -> None:
        """Test that False values are also cached."""
        wrapped = Mock(spec=PrimaryDetector)
        wrapped.is_primary.return_value = False

        cached = CachedPrimaryDetector(wrapped, ttl_seconds=10.0)

        assert cached.is_primary() is False
        assert cached.is_primary() is False
        assert wrapped.is_primary.call_count == 1

    def test_wraps_primary_detector_interface(self, tmp_path) -> None:
        """Test that CachedPrimaryDetector works with real PrimaryDetector."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        real_detector = PrimaryDetector(mount_path=str(mount_path))
        cached = CachedPrimaryDetector(real_detector, ttl_seconds=10.0)

        assert cached.is_primary() is True
