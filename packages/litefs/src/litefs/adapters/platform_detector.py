"""Platform detector adapter for detecting current OS and architecture.

This module provides an adapter that implements PlatformDetectorPort
by using Python's standard library platform module.
"""

from __future__ import annotations

import platform
from typing import Literal

from litefs.domain.binary import Platform
from litefs.domain.exceptions import LiteFSConfigError


class OsPlatformDetector:
    """Adapter that detects the current platform using platform module.

    Implements PlatformDetectorPort by querying platform.system() and
    platform.machine() to determine the current OS and architecture.

    Supported platforms:
        - OS: linux, darwin
        - Architecture: amd64, arm64

    Machine type mappings:
        - x86_64, AMD64 -> amd64
        - aarch64, arm64 -> arm64
    """

    # Mapping from platform.system() values to our normalized OS names
    _OS_MAP: dict[str, Literal["linux", "darwin"]] = {
        "linux": "linux",
        "darwin": "darwin",
    }

    # Mapping from platform.machine() values to our normalized arch names
    _ARCH_MAP: dict[str, Literal["amd64", "arm64"]] = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }

    def detect(self) -> Platform:
        """Detect the current platform.

        Uses platform.system() for OS detection and platform.machine()
        for architecture detection. Values are normalized and mapped
        to our supported platform identifiers.

        Returns:
            Platform value object with os and arch fields.

        Raises:
            LiteFSConfigError: If the current OS or architecture is not supported.
        """
        os_name = self._detect_os()
        arch_name = self._detect_arch()
        return Platform(os=os_name, arch=arch_name)

    def _detect_os(self) -> Literal["linux", "darwin"]:
        """Detect and normalize the operating system.

        Returns:
            Normalized OS name ('linux' or 'darwin').

        Raises:
            LiteFSConfigError: If the current OS is not supported.
        """
        system = platform.system().lower()
        if system not in self._OS_MAP:
            raise LiteFSConfigError(
                f"Unsupported operating system: {platform.system()!r}. "
                f"Supported: linux, darwin"
            )
        return self._OS_MAP[system]

    def _detect_arch(self) -> Literal["amd64", "arm64"]:
        """Detect and normalize the CPU architecture.

        Returns:
            Normalized architecture name ('amd64' or 'arm64').

        Raises:
            LiteFSConfigError: If the current architecture is not supported.
        """
        machine = platform.machine().lower()
        if machine not in self._ARCH_MAP:
            raise LiteFSConfigError(
                f"Unsupported architecture: {platform.machine()!r}. "
                f"Supported: x86_64/amd64, aarch64/arm64"
            )
        return self._ARCH_MAP[machine]
