"""Fake platform detector for testing.

This module provides a fake implementation of PlatformDetectorPort
that allows tests to control platform detection without relying on
actual OS/architecture detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

from litefs.domain.binary import Platform


class FakePlatformDetector:
    """Fake implementation of PlatformDetectorPort for testing.

    Allows tests to configure the platform that will be returned
    by detect(), enabling deterministic testing of platform-dependent
    logic without relying on actual OS/architecture detection.

    Example:
        >>> fake = FakePlatformDetector(Platform(os="linux", arch="amd64"))
        >>> fake.detect()
        Platform(os='linux', arch='amd64')

        >>> fake = FakePlatformDetector.from_tuple("darwin", "arm64")
        >>> fake.detect()
        Platform(os='darwin', arch='arm64')
    """

    def __init__(self, platform: Platform) -> None:
        """Initialize with the platform to return.

        Args:
            platform: The Platform value object to return from detect().
        """
        self._platform = platform

    @classmethod
    def from_tuple(
        cls,
        os: Literal["linux", "darwin"],
        arch: Literal["amd64", "arm64"],
    ) -> FakePlatformDetector:
        """Create a FakePlatformDetector from OS and architecture strings.

        Convenience constructor for when you don't want to import Platform.

        Args:
            os: Operating system ('linux' or 'darwin').
            arch: Architecture ('amd64' or 'arm64').

        Returns:
            FakePlatformDetector configured with the specified platform.
        """
        return cls(Platform(os=os, arch=arch))

    def detect(self) -> Platform:
        """Return the configured platform.

        Returns:
            The Platform value object configured at construction time.
        """
        return self._platform
