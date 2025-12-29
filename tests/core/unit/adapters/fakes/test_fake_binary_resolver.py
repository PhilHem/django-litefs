"""Tests for FakeBinaryResolver test double."""

from __future__ import annotations

from pathlib import Path

import pytest

from litefs.adapters.fakes.fake_binary_resolver import FakeBinaryResolver
from litefs.adapters.ports import BinaryResolverPort
from litefs.domain.binary import BinaryLocation


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryResolver")
class TestFakeBinaryResolver:
    """Tests for FakeBinaryResolver fake adapter."""

    def test_satisfies_protocol(self) -> None:
        """FakeBinaryResolver satisfies BinaryResolverPort protocol."""
        fake = FakeBinaryResolver(location=None)
        assert isinstance(fake, BinaryResolverPort)

    def test_resolve_returns_configured_location(self) -> None:
        """resolve() returns preconfigured BinaryLocation."""
        location = BinaryLocation(path=Path("/usr/bin/litefs"), is_custom=False)
        fake = FakeBinaryResolver(location=location)

        result = fake.resolve()

        assert result is location

    def test_resolve_returns_none_when_configured(self) -> None:
        """resolve() returns None when configured with None."""
        fake = FakeBinaryResolver(location=None)

        result = fake.resolve()

        assert result is None

    def test_configurable_path_default_location(self) -> None:
        """FakeBinaryResolver supports configurable path with is_custom=False."""
        location = BinaryLocation(path=Path("/opt/litefs/bin/litefs"), is_custom=False)
        fake = FakeBinaryResolver(location=location)

        result = fake.resolve()

        assert result is not None
        assert result.path == Path("/opt/litefs/bin/litefs")
        assert result.is_custom is False

    def test_configurable_path_custom_location(self) -> None:
        """FakeBinaryResolver supports configurable path with is_custom=True."""
        location = BinaryLocation(path=Path("/home/user/litefs"), is_custom=True)
        fake = FakeBinaryResolver(location=location)

        result = fake.resolve()

        assert result is not None
        assert result.path == Path("/home/user/litefs")
        assert result.is_custom is True

    def test_multiple_calls_return_same_value(self) -> None:
        """Multiple calls to resolve() return the same configured value."""
        location = BinaryLocation(path=Path("/usr/bin/litefs"), is_custom=False)
        fake = FakeBinaryResolver(location=location)

        result1 = fake.resolve()
        result2 = fake.resolve()
        result3 = fake.resolve()

        assert result1 is result2 is result3 is location
