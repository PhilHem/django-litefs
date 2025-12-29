"""Unit tests for BinaryDownloader use case."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from litefs.adapters.ports import BinaryDownloaderPort
from litefs.domain.binary import (
    BinaryLocation,
    BinaryMetadata,
    BinaryVersion,
    Platform,
)
from litefs.usecases.binary_downloader import BinaryDownloader, BinaryDownloadResult


@pytest.fixture
def sample_platform() -> Platform:
    """Create a sample platform for testing."""
    return Platform(os="linux", arch="amd64")


@pytest.fixture
def sample_version() -> BinaryVersion:
    """Create a sample version for testing."""
    return BinaryVersion(major=0, minor=8, patch=0)


@pytest.fixture
def sample_location() -> BinaryLocation:
    """Create a sample location for testing."""
    return BinaryLocation(path=Path("/usr/local/bin/litefs"), is_custom=False)


@pytest.fixture
def sample_metadata(
    sample_platform: Platform,
    sample_version: BinaryVersion,
    sample_location: BinaryLocation,
) -> BinaryMetadata:
    """Create sample binary metadata for testing."""
    return BinaryMetadata(
        platform=sample_platform,
        version=sample_version,
        location=sample_location,
    )


@pytest.fixture
def downloaded_metadata(
    sample_platform: Platform,
    sample_version: BinaryVersion,
) -> BinaryMetadata:
    """Create binary metadata as returned by port after download."""
    return BinaryMetadata(
        platform=sample_platform,
        version=sample_version,
        location=BinaryLocation(path=Path("/tmp/litefs"), is_custom=False),
        checksum="abc123",
        size_bytes=1024,
        downloaded_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def mock_downloader_port(downloaded_metadata: BinaryMetadata) -> Mock:
    """Create a mock BinaryDownloaderPort."""
    port = Mock(spec=BinaryDownloaderPort)
    port.download.return_value = downloaded_metadata
    return port


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.BinaryDownloader")
class TestBinaryDownloader:
    """Test BinaryDownloader use case."""

    def test_download_success_returns_success_result(
        self,
        mock_downloader_port: Mock,
        downloaded_metadata: BinaryMetadata,
    ) -> None:
        """Test that successful download returns success result."""
        downloader = BinaryDownloader(port=mock_downloader_port)
        url = "https://github.com/superfly/litefs/releases/download/v0.8.0/litefs-linux-amd64"
        destination = Path("/tmp/litefs")

        result = downloader.download(url=url, destination=destination)

        assert result.success is True
        assert result.metadata == downloaded_metadata
        assert result.error is None

    def test_download_delegates_to_port(
        self,
        mock_downloader_port: Mock,
    ) -> None:
        """Test that download delegates to port with correct arguments."""
        downloader = BinaryDownloader(port=mock_downloader_port)
        url = "https://example.com/litefs"
        destination = Path("/opt/litefs")

        downloader.download(url=url, destination=destination)

        mock_downloader_port.download.assert_called_once_with(url, destination)

    def test_download_returns_metadata_from_port(
        self,
        mock_downloader_port: Mock,
        downloaded_metadata: BinaryMetadata,
    ) -> None:
        """Test that result contains metadata from port."""
        downloader = BinaryDownloader(port=mock_downloader_port)
        url = "https://example.com/litefs"
        destination = Path("/tmp/litefs")

        result = downloader.download(url=url, destination=destination)

        assert result.metadata is downloaded_metadata
        assert result.metadata.checksum == "abc123"
        assert result.metadata.size_bytes == 1024

    def test_download_handles_port_error(
        self,
        mock_downloader_port: Mock,
    ) -> None:
        """Test that port errors are captured in result."""
        mock_downloader_port.download.side_effect = OSError("Network error")
        downloader = BinaryDownloader(port=mock_downloader_port)
        url = "https://example.com/litefs"
        destination = Path("/tmp/litefs")

        result = downloader.download(url=url, destination=destination)

        assert result.success is False
        assert result.metadata is None
        assert result.error == "Network error"

    def test_download_handles_generic_exception(
        self,
        mock_downloader_port: Mock,
    ) -> None:
        """Test that generic exceptions are captured in result."""
        mock_downloader_port.download.side_effect = RuntimeError("Unexpected error")
        downloader = BinaryDownloader(port=mock_downloader_port)
        url = "https://example.com/litefs"
        destination = Path("/tmp/litefs")

        result = downloader.download(url=url, destination=destination)

        assert result.success is False
        assert result.metadata is None
        assert result.error == "Unexpected error"

    def test_download_result_success_factory(
        self,
        downloaded_metadata: BinaryMetadata,
    ) -> None:
        """Test BinaryDownloadResult.success factory method."""
        result = BinaryDownloadResult.create_success(downloaded_metadata)

        assert result.success is True
        assert result.metadata == downloaded_metadata
        assert result.error is None

    def test_download_result_failure_factory(self) -> None:
        """Test BinaryDownloadResult.failure factory method."""
        result = BinaryDownloadResult.create_failure("Download failed")

        assert result.success is False
        assert result.metadata is None
        assert result.error == "Download failed"
