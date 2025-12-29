"""Unit tests for HttpxBinaryDownloader adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import httpx
import pytest

from litefs.adapters.httpx_binary_downloader import HttpxBinaryDownloader
from litefs.adapters.ports import BinaryDownloaderPort
from litefs.domain.binary import (
    BinaryMetadata,
    BinaryVersion,
    BinaryLocation,
    Platform,
)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.HttpxBinaryDownloader")
class TestHttpxBinaryDownloaderProtocol:
    """Test HttpxBinaryDownloader satisfies BinaryDownloaderPort protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that HttpxBinaryDownloader is instance of BinaryDownloaderPort."""
        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
        )
        assert isinstance(downloader, BinaryDownloaderPort)

    def test_has_download_method(self) -> None:
        """Test that HttpxBinaryDownloader has download method."""
        assert hasattr(HttpxBinaryDownloader, "download")


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.HttpxBinaryDownloader")
class TestHttpxBinaryDownloaderDownload:
    """Test HttpxBinaryDownloader.download() method."""

    def test_download_success_returns_metadata(self, tmp_path: Path) -> None:
        """Test successful download returns BinaryMetadata."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        result = downloader.download("https://example.com/litefs", destination)

        assert isinstance(result, BinaryMetadata)
        assert result.platform.os == "linux"
        assert result.platform.arch == "amd64"
        assert result.version.major == 0
        assert result.version.minor == 8
        assert result.version.patch == 0
        assert result.location.path == destination
        assert result.location.is_custom is False

    def test_download_computes_sha256_checksum(self, tmp_path: Path) -> None:
        """Test download computes SHA256 checksum of downloaded content."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"
        expected_checksum = hashlib.sha256(binary_content).hexdigest()

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        result = downloader.download("https://example.com/litefs", destination)

        assert result.checksum == expected_checksum

    def test_download_sets_size_bytes(self, tmp_path: Path) -> None:
        """Test download sets size_bytes to content length."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        result = downloader.download("https://example.com/litefs", destination)

        assert result.size_bytes == len(binary_content)

    def test_download_sets_downloaded_at(self, tmp_path: Path) -> None:
        """Test download sets downloaded_at timestamp."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        before = datetime.now(timezone.utc)
        result = downloader.download("https://example.com/litefs", destination)
        after = datetime.now(timezone.utc)

        assert result.downloaded_at is not None
        assert before <= result.downloaded_at <= after

    def test_download_writes_content_to_destination(self, tmp_path: Path) -> None:
        """Test download writes binary content to destination path."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        downloader.download("https://example.com/litefs", destination)

        assert destination.exists()
        assert destination.read_bytes() == binary_content

    def test_network_error_propagates(self, tmp_path: Path) -> None:
        """Test that network errors are propagated (not caught)."""
        destination = tmp_path / "litefs"

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        with pytest.raises(httpx.ConnectError):
            downloader.download("https://example.com/litefs", destination)

    def test_http_error_propagates(self, tmp_path: Path) -> None:
        """Test that HTTP errors (4xx, 5xx) are propagated."""
        destination = tmp_path / "litefs"

        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=Mock(status_code=404),
        )

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        with pytest.raises(httpx.HTTPStatusError):
            downloader.download("https://example.com/litefs", destination)

    def test_filesystem_error_propagates(self, tmp_path: Path) -> None:
        """Test that filesystem errors are propagated."""
        # Use a non-existent parent directory
        destination = tmp_path / "nonexistent" / "subdir" / "litefs"
        binary_content = b"fake litefs binary content"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        with pytest.raises(OSError):
            downloader.download("https://example.com/litefs", destination)

    def test_download_uses_provided_url(self, tmp_path: Path) -> None:
        """Test download calls httpx.get with the provided URL."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"
        test_url = "https://github.com/superfly/litefs/releases/download/v0.8.0/litefs-linux-amd64"

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        mock_client = Mock(spec=httpx.Client)
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            client=mock_client,
        )

        downloader.download(test_url, destination)

        mock_client.get.assert_called_once_with(test_url)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.HttpxBinaryDownloader")
class TestHttpxBinaryDownloaderWithoutInjectedClient:
    """Test HttpxBinaryDownloader without injected client (creates its own)."""

    def test_creates_client_when_none_provided(self, tmp_path: Path) -> None:
        """Test that downloader creates httpx.Client when none injected."""
        destination = tmp_path / "litefs"
        binary_content = b"fake litefs binary content"

        downloader = HttpxBinaryDownloader(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
        )

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = binary_content
        mock_response.raise_for_status = Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            result = downloader.download("https://example.com/litefs", destination)

            mock_client_class.assert_called_once()
            assert isinstance(result, BinaryMetadata)
