"""Unit tests for FakeBinaryDownloader test double."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from litefs.adapters.fakes.fake_binary_downloader import FakeBinaryDownloader
from litefs.adapters.ports import BinaryDownloaderPort
from litefs.domain.binary import (
    BinaryLocation,
    BinaryMetadata,
    BinaryVersion,
    Platform,
)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryDownloader")
class TestFakeBinaryDownloaderProtocol:
    """Test FakeBinaryDownloader implements BinaryDownloaderPort protocol."""

    def test_implements_binary_downloader_port_protocol(self) -> None:
        """Test that FakeBinaryDownloader satisfies BinaryDownloaderPort protocol."""
        fake = FakeBinaryDownloader()
        assert isinstance(fake, BinaryDownloaderPort)

    def test_has_download_method(self) -> None:
        """Test that FakeBinaryDownloader has download method with correct signature."""
        fake = FakeBinaryDownloader()
        assert hasattr(fake, "download")
        assert callable(fake.download)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryDownloader")
class TestFakeBinaryDownloaderDownload:
    """Test FakeBinaryDownloader.download() behavior."""

    def test_download_returns_configured_metadata(self) -> None:
        """Test download() returns pre-configured BinaryMetadata."""
        expected_metadata = BinaryMetadata(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            location=BinaryLocation(path=Path("/tmp/litefs"), is_custom=False),
        )
        fake = FakeBinaryDownloader(metadata=expected_metadata)

        result = fake.download("http://example.com/litefs", Path("/tmp/litefs"))

        assert result == expected_metadata

    def test_download_with_default_metadata(self) -> None:
        """Test download() returns default metadata when none configured."""
        fake = FakeBinaryDownloader()

        result = fake.download("http://example.com/litefs", Path("/tmp/litefs"))

        assert isinstance(result, BinaryMetadata)
        assert result.platform.os == "linux"
        assert result.platform.arch == "amd64"
        assert result.version == BinaryVersion(major=0, minor=8, patch=0)

    def test_download_uses_destination_in_default_metadata(self) -> None:
        """Test default metadata uses provided destination path."""
        fake = FakeBinaryDownloader()
        dest = Path("/custom/path/litefs")

        result = fake.download("http://example.com/litefs", dest)

        assert result.location.path == dest

    def test_download_raises_configured_exception(self) -> None:
        """Test download() raises configured exception."""
        fake = FakeBinaryDownloader()
        fake.set_exception(IOError("Network error"))

        with pytest.raises(IOError, match="Network error"):
            fake.download("http://example.com/litefs", Path("/tmp/litefs"))

    def test_download_raises_custom_exception_type(self) -> None:
        """Test download() raises custom exception types."""

        @dataclass
        class CustomDownloadError(Exception):
            message: str

        fake = FakeBinaryDownloader()
        fake.set_exception(CustomDownloadError("Custom error"))

        with pytest.raises(CustomDownloadError):
            fake.download("http://example.com/litefs", Path("/tmp/litefs"))


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryDownloader")
class TestFakeBinaryDownloaderConfiguration:
    """Test FakeBinaryDownloader configuration methods."""

    def test_set_response_updates_metadata(self) -> None:
        """Test set_response() updates the metadata to return."""
        fake = FakeBinaryDownloader()
        new_metadata = BinaryMetadata(
            platform=Platform(os="darwin", arch="arm64"),
            version=BinaryVersion(major=1, minor=0, patch=0),
            location=BinaryLocation(path=Path("/opt/litefs"), is_custom=True),
        )

        fake.set_response(new_metadata)
        result = fake.download("http://example.com/litefs", Path("/tmp/litefs"))

        assert result == new_metadata

    def test_set_exception_enables_exception_raising(self) -> None:
        """Test set_exception() configures exception to raise."""
        fake = FakeBinaryDownloader()

        fake.set_exception(ValueError("Invalid URL"))

        with pytest.raises(ValueError, match="Invalid URL"):
            fake.download("http://example.com/litefs", Path("/tmp/litefs"))

    def test_set_exception_none_clears_exception(self) -> None:
        """Test set_exception(None) clears configured exception."""
        fake = FakeBinaryDownloader()
        fake.set_exception(IOError("Error"))

        fake.set_exception(None)
        result = fake.download("http://example.com/litefs", Path("/tmp/litefs"))

        assert isinstance(result, BinaryMetadata)

    def test_exception_takes_precedence_over_response(self) -> None:
        """Test that exception is raised even when metadata is configured."""
        metadata = BinaryMetadata(
            platform=Platform(os="linux", arch="amd64"),
            version=BinaryVersion(major=0, minor=8, patch=0),
            location=BinaryLocation(path=Path("/tmp/litefs"), is_custom=False),
        )
        fake = FakeBinaryDownloader(metadata=metadata)
        fake.set_exception(RuntimeError("Download failed"))

        with pytest.raises(RuntimeError, match="Download failed"):
            fake.download("http://example.com/litefs", Path("/tmp/litefs"))


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryDownloader")
class TestFakeBinaryDownloaderCallRecording:
    """Test FakeBinaryDownloader call recording for assertions."""

    def test_records_calls_for_assertion(self) -> None:
        """Test that download() calls are recorded."""
        fake = FakeBinaryDownloader()

        fake.download("http://example.com/v1", Path("/tmp/v1"))
        fake.download("http://example.com/v2", Path("/tmp/v2"))

        assert len(fake.calls) == 2
        assert fake.calls[0] == ("http://example.com/v1", Path("/tmp/v1"))
        assert fake.calls[1] == ("http://example.com/v2", Path("/tmp/v2"))

    def test_calls_empty_initially(self) -> None:
        """Test that calls list is empty initially."""
        fake = FakeBinaryDownloader()

        assert fake.calls == []

    def test_clear_calls_resets_recorded_calls(self) -> None:
        """Test clear_calls() resets the recorded calls list."""
        fake = FakeBinaryDownloader()
        fake.download("http://example.com/litefs", Path("/tmp/litefs"))
        assert len(fake.calls) == 1

        fake.clear_calls()

        assert fake.calls == []

    def test_calls_recorded_even_when_exception_raised(self) -> None:
        """Test that calls are recorded even when exception is raised."""
        fake = FakeBinaryDownloader()
        fake.set_exception(IOError("Error"))

        with pytest.raises(IOError):
            fake.download("http://example.com/litefs", Path("/tmp/litefs"))

        assert len(fake.calls) == 1
        assert fake.calls[0] == ("http://example.com/litefs", Path("/tmp/litefs"))


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeBinaryDownloader")
class TestFakeBinaryDownloaderNoSideEffects:
    """Test FakeBinaryDownloader has no filesystem side effects."""

    def test_no_side_effects_on_filesystem(self, tmp_path: Path) -> None:
        """Test download() does not create files on filesystem."""
        fake = FakeBinaryDownloader()
        dest = tmp_path / "litefs"

        fake.download("http://example.com/litefs", dest)

        assert not dest.exists()

    def test_no_network_calls_made(self) -> None:
        """Test download() is purely in-memory, no network access."""
        # This test verifies the contract: FakeBinaryDownloader should
        # never make network calls. The implementation is purely in-memory.
        fake = FakeBinaryDownloader()

        # If this made network calls, it would fail or hang on invalid URL
        result = fake.download("not-a-valid-url://invalid", Path("/tmp/litefs"))

        assert isinstance(result, BinaryMetadata)
