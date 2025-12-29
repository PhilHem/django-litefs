"""Binary-related domain value objects.

This module contains value objects for managing LiteFS binary metadata,
including platform information, version handling, and binary location tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class Platform:
    """Platform value object representing OS and architecture.

    Immutable value object that holds the target platform information
    for the LiteFS binary.

    Attributes:
        os: Operating system, must be 'linux' or 'darwin'.
        arch: Architecture, must be 'amd64' or 'arm64'.
    """

    os: Literal["linux", "darwin"]
    arch: Literal["amd64", "arm64"]

    def __post_init__(self) -> None:
        """Validate platform configuration."""
        self._validate_os()
        self._validate_arch()

    def _validate_os(self) -> None:
        """Validate os is a valid value."""
        valid_os = ("linux", "darwin")
        if self.os not in valid_os:
            raise LiteFSConfigError(f"os must be one of {valid_os}, got: {self.os!r}")

    def _validate_arch(self) -> None:
        """Validate arch is a valid value."""
        valid_arch = ("amd64", "arm64")
        if self.arch not in valid_arch:
            raise LiteFSConfigError(
                f"arch must be one of {valid_arch}, got: {self.arch!r}"
            )


@dataclass(frozen=True, order=True)
class BinaryVersion:
    """Binary version value object with semantic versioning support.

    Immutable value object representing a semantic version (major.minor.patch).
    Supports comparison operations for version ordering.

    Attributes:
        major: Major version number (non-negative).
        minor: Minor version number (non-negative).
        patch: Patch version number (non-negative).
    """

    major: int
    minor: int
    patch: int

    def __post_init__(self) -> None:
        """Validate version components."""
        self._validate_components()

    def _validate_components(self) -> None:
        """Validate all version components are non-negative."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise LiteFSConfigError(
                f"Version components must be non-negative, got: {self.major}.{self.minor}.{self.patch}"
            )

    @classmethod
    def from_string(cls, version_string: str) -> BinaryVersion:
        """Parse a version from string format.

        Accepts versions like '0.8.0', 'v1.2.3', '10.20.30'.

        Args:
            version_string: Version string to parse.

        Returns:
            BinaryVersion instance.

        Raises:
            LiteFSConfigError: If version format is invalid.
        """
        # Strip optional 'v' prefix
        version = version_string.lstrip("v")

        parts = version.split(".")
        if len(parts) != 3:
            raise LiteFSConfigError(
                f"Invalid version format, expected 'X.Y.Z', got: {version_string!r}"
            )

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError:
            raise LiteFSConfigError(
                f"Invalid version format, expected numeric components, got: {version_string!r}"
            )

        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:
        """Return string representation of version."""
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class BinaryLocation:
    """Binary location value object.

    Immutable value object representing where the LiteFS binary is located,
    either as a local filesystem path or a custom user-specified location.

    Attributes:
        path: Path to the binary location.
        is_custom: True if user-specified, False if using default location.
    """

    path: Path
    is_custom: bool

    def __post_init__(self) -> None:
        """Validate location configuration."""
        self._validate_path()

    def _validate_path(self) -> None:
        """Validate path is not empty."""
        # Path("") creates PosixPath('.'), so check string representation
        path_str = str(self.path)
        if not path_str or path_str == ".":
            raise LiteFSConfigError("path cannot be empty")


@dataclass(frozen=True)
class BinaryMetadata:
    """Binary metadata value object.

    Immutable value object composed of Platform, BinaryVersion, and BinaryLocation,
    with optional fields for tracking binary provenance.

    Attributes:
        platform: Target platform for the binary.
        version: Version of the binary.
        location: Where the binary is located.
        checksum: Optional SHA256 hash of the binary.
        size_bytes: Optional size of the binary in bytes.
        downloaded_at: Optional timestamp when the binary was downloaded.
    """

    platform: Platform
    version: BinaryVersion
    location: BinaryLocation
    checksum: str | None = None
    size_bytes: int | None = None
    downloaded_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate metadata configuration."""
        self._validate_size_bytes()
        self._validate_checksum()

    def _validate_size_bytes(self) -> None:
        """Validate size_bytes is non-negative if provided."""
        if self.size_bytes is not None and self.size_bytes < 0:
            raise LiteFSConfigError(
                f"size_bytes must be non-negative, got: {self.size_bytes}"
            )

    def _validate_checksum(self) -> None:
        """Validate checksum is not empty if provided."""
        if self.checksum is not None and not self.checksum:
            raise LiteFSConfigError("checksum cannot be empty if provided")
