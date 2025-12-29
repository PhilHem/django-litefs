"""Binary downloader use case for orchestrating LiteFS binary downloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litefs.adapters.ports import BinaryDownloaderPort
    from litefs.domain.binary import BinaryMetadata


@dataclass(frozen=True)
class BinaryDownloadResult:
    """Result of a binary download operation.

    Immutable value object containing the outcome of a download attempt,
    including success status, optional metadata, and optional error message.

    Attributes:
        success: True if download succeeded, False otherwise.
        metadata: BinaryMetadata if download succeeded, None otherwise.
        error: Error message if download failed, None otherwise.
    """

    success: bool
    metadata: BinaryMetadata | None
    error: str | None

    @classmethod
    def create_success(cls, metadata: BinaryMetadata) -> BinaryDownloadResult:
        """Create a success result with metadata.

        Args:
            metadata: The downloaded binary metadata.

        Returns:
            BinaryDownloadResult indicating success.
        """
        return cls(success=True, metadata=metadata, error=None)

    @classmethod
    def create_failure(cls, error: str) -> BinaryDownloadResult:
        """Create a failure result with error message.

        Args:
            error: Description of the error that occurred.

        Returns:
            BinaryDownloadResult indicating failure.
        """
        return cls(success=False, metadata=None, error=error)


class BinaryDownloader:
    """Orchestrates LiteFS binary download operations.

    Use case that coordinates between domain value objects and port interfaces
    to fetch and prepare binaries. Delegates actual download to the provided
    port implementation.

    This is a stateless orchestration component with zero framework dependencies.
    """

    def __init__(self, port: BinaryDownloaderPort) -> None:
        """Initialize the binary downloader.

        Args:
            port: BinaryDownloaderPort implementation for actual download.
        """
        self._port = port

    def download(self, url: str, destination: Path) -> BinaryDownloadResult:
        """Download a LiteFS binary from URL to destination.

        Orchestrates the download operation by delegating to the port
        and wrapping the result in a BinaryDownloadResult.

        Args:
            url: Remote URL to download the binary from.
            destination: Local filesystem path to save the binary to.

        Returns:
            BinaryDownloadResult containing success status, metadata (on success),
            or error message (on failure).
        """
        try:
            metadata = self._port.download(url, destination)
            return BinaryDownloadResult.create_success(metadata)
        except Exception as e:
            return BinaryDownloadResult.create_failure(str(e))
