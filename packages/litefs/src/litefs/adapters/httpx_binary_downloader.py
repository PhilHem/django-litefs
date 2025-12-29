"""HTTPX-based implementation of the BinaryDownloaderPort.

This adapter uses httpx to download LiteFS binary from remote URLs.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import httpx

from litefs.adapters.ports import BinaryDownloaderPort
from litefs.domain.binary import (
    BinaryLocation,
    BinaryMetadata,
    BinaryVersion,
    Platform,
)


class HttpxBinaryDownloader:
    """HTTPX-based adapter for downloading LiteFS binary.

    Uses httpx to download the LiteFS binary from a remote URL and save it
    to a local filesystem path. Computes SHA256 checksum and tracks metadata.

    This adapter implements BinaryDownloaderPort for use by binary management
    use cases.

    Attributes:
        platform: Target platform (os and arch) for the binary.
        version: Version of the binary being downloaded.
    """

    def __init__(
        self,
        platform: Platform,
        version: BinaryVersion,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the HTTPX binary downloader.

        Args:
            platform: Target platform for the binary.
            version: Version of the binary to download.
            client: Optional httpx.Client for dependency injection (testing).
                   If not provided, a new client is created per request.
        """
        self._platform = platform
        self._version = version
        self._client = client

    def download(self, url: str, destination: Path) -> BinaryMetadata:
        """Download binary from URL to local filesystem.

        Fetches the binary from the provided URL, saves it to the destination
        path, and computes metadata including SHA256 checksum.

        Args:
            url: Remote URL to download the binary from.
            destination: Local filesystem path to save the binary to.
                The parent directory must exist.

        Returns:
            BinaryMetadata containing platform, version, location, checksum,
            size_bytes, and downloaded_at.

        Raises:
            httpx.RequestError: For network failures.
            httpx.HTTPStatusError: For HTTP errors (4xx, 5xx).
            OSError: For filesystem errors (e.g., parent directory not found).
        """
        if self._client is not None:
            response = self._client.get(url)
            response.raise_for_status()
            content = response.content
        else:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                content = response.content

        # Write content to destination
        destination.write_bytes(content)

        # Compute SHA256 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Get current timestamp
        downloaded_at = datetime.now(timezone.utc)

        return BinaryMetadata(
            platform=self._platform,
            version=self._version,
            location=BinaryLocation(path=destination, is_custom=False),
            checksum=checksum,
            size_bytes=len(content),
            downloaded_at=downloaded_at,
        )


# Runtime protocol check
assert isinstance(
    HttpxBinaryDownloader(
        platform=Platform(os="linux", arch="amd64"),
        version=BinaryVersion(major=0, minor=8, patch=0),
    ),
    BinaryDownloaderPort,
)
