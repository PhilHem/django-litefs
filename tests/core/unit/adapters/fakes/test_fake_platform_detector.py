"""Unit tests for FakePlatformDetector."""

from __future__ import annotations

import pytest

from litefs.adapters.fakes.fake_platform_detector import FakePlatformDetector
from litefs.adapters.ports import PlatformDetectorPort
from litefs.domain.binary import Platform


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakePlatformDetector")
class TestFakePlatformDetector:
    """Test suite for FakePlatformDetector."""

    def test_implements_protocol(self) -> None:
        """FakePlatformDetector implements PlatformDetectorPort protocol."""
        fake = FakePlatformDetector(Platform(os="linux", arch="amd64"))
        assert isinstance(fake, PlatformDetectorPort)

    def test_returns_configured_platform(self) -> None:
        """detect() returns the configured Platform value object."""
        platform = Platform(os="linux", arch="amd64")
        fake = FakePlatformDetector(platform)
        result = fake.detect()
        assert result == platform
        assert result is platform

    def test_with_linux_amd64(self) -> None:
        """Works with linux/amd64 platform combination."""
        platform = Platform(os="linux", arch="amd64")
        fake = FakePlatformDetector(platform)
        result = fake.detect()
        assert result.os == "linux"
        assert result.arch == "amd64"

    def test_with_linux_arm64(self) -> None:
        """Works with linux/arm64 platform combination."""
        platform = Platform(os="linux", arch="arm64")
        fake = FakePlatformDetector(platform)
        result = fake.detect()
        assert result.os == "linux"
        assert result.arch == "arm64"

    def test_with_darwin_amd64(self) -> None:
        """Works with darwin/amd64 platform combination."""
        platform = Platform(os="darwin", arch="amd64")
        fake = FakePlatformDetector(platform)
        result = fake.detect()
        assert result.os == "darwin"
        assert result.arch == "amd64"

    def test_with_darwin_arm64(self) -> None:
        """Works with darwin/arm64 platform combination."""
        platform = Platform(os="darwin", arch="arm64")
        fake = FakePlatformDetector(platform)
        result = fake.detect()
        assert result.os == "darwin"
        assert result.arch == "arm64"

    def test_from_tuple(self) -> None:
        """Can be constructed from (os, arch) tuple."""
        fake = FakePlatformDetector.from_tuple("darwin", "arm64")
        result = fake.detect()
        assert result.os == "darwin"
        assert result.arch == "arm64"

    def test_detect_is_idempotent(self) -> None:
        """Multiple calls to detect() return the same result."""
        platform = Platform(os="linux", arch="amd64")
        fake = FakePlatformDetector(platform)
        result1 = fake.detect()
        result2 = fake.detect()
        assert result1 == result2
        assert result1 is result2

    def test_can_be_injected_into_use_case(self) -> None:
        """Fake can be used as dependency injection in use cases."""
        # Simulate a use case that accepts PlatformDetectorPort
        def use_case(detector: PlatformDetectorPort) -> str:
            platform = detector.detect()
            return f"{platform.os}-{platform.arch}"

        fake = FakePlatformDetector(Platform(os="darwin", arch="arm64"))
        result = use_case(fake)
        assert result == "darwin-arm64"
