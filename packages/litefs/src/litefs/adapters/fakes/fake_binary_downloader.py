"""Fake binary downloader for testing.

Provides a test double for BinaryDownloaderPort that returns
preconfigured values without network operations.
"""

from __future__ import annotations

from pathlib import Path

from litefs.domain.binary import (
    BinaryLocation,
    BinaryMetadata,
    BinaryVersion,
    Platform,
)


class FakeBinaryDownloader:
    """Fake implementation of BinaryDownloaderPort for testing.

    Returns preconfigured BinaryMetadata without making network calls.
    Supports configuring exceptions for error path testing and records
    all calls for assertion in tests.

    Example:
        >>> from pathlib import Path
        >>> metadata = BinaryMetadata(
        ...     platform=Platform(os="linux", arch="amd64"),
        ...     version=BinaryVersion(major=0, minor=8, patch=0),
        ...     location=BinaryLocation(path=Path("/tmp/litefs"), is_custom=False),
        ... )
        >>> fake = FakeBinaryDownloader(metadata=metadata)
        >>> result = fake.download("http://example.com/litefs", Path("/tmp/litefs"))
        >>> result == metadata
        True
    """

    def __init__(self, metadata: BinaryMetadata | None = None) -> None:
        """Initialize with optional preconfigured response.

        Args:
            metadata: BinaryMetadata to return from download().
                If None, a default metadata will be generated using
                the destination path from the download() call.
        """
        self._metadata = metadata
        self._exception: BaseException | None = None
        self._calls: list[tuple[str, Path]] = []

    @property
    def calls(self) -> list[tuple[str, Path]]:
        """Return list of (url, destination) tuples from download() calls.

        Returns:
            List of recorded calls as (url, destination) tuples.
        """
        return self._calls

    def set_response(self, metadata: BinaryMetadata) -> None:
        """Configure the metadata to return from download().

        Args:
            metadata: BinaryMetadata to return on subsequent download() calls.
        """
        self._metadata = metadata

    def set_exception(self, exception: BaseException | None) -> None:
        """Configure an exception to raise from download().

        Args:
            exception: Exception to raise on download(), or None to clear.
        """
        self._exception = exception

    def clear_calls(self) -> None:
        """Clear the recorded calls list."""
        self._calls.clear()

    def download(self, url: str, destination: Path) -> BinaryMetadata:
        """Return preconfigured metadata or raise configured exception.

        Records the call for later assertion, then either raises the
        configured exception or returns the configured metadata.

        Args:
            url: URL argument (recorded but not used).
            destination: Destination path (used in default metadata).

        Returns:
            The preconfigured BinaryMetadata, or a default metadata
            using the destination path if none was configured.

        Raises:
            Any exception configured via set_exception().
        """
        self._calls.append((url, destination))

        if self._exception is not None:
            raise self._exception

        if self._metadata is not None:
            return self._metadata

        # Return default metadata using the destination path
        return BinaryMetadata(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            location=BinaryLocation(path=destination, is_custom=False),
        )
