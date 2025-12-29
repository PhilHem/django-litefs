"""Tests for domain exceptions."""

import pytest

from litefs.domain.exceptions import BinaryDownloadError, LiteFSConfigError


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.Exception")
class TestBinaryDownloadError:
    """Tests for BinaryDownloadError exception."""

    def test_inherits_from_litefs_config_error(self) -> None:
        """BinaryDownloadError should inherit from LiteFSConfigError."""
        error = BinaryDownloadError("download failed")
        assert isinstance(error, LiteFSConfigError)
        assert isinstance(error, Exception)

    def test_stores_message(self) -> None:
        """Error should store and expose message."""
        error = BinaryDownloadError("download failed")
        assert error.message == "download failed"
        assert str(error) == "download failed"

    def test_stores_url(self) -> None:
        """Error should store URL when provided."""
        error = BinaryDownloadError("failed", url="https://example.com/binary")
        assert error.url == "https://example.com/binary"

    def test_stores_original_error(self) -> None:
        """Error should store original exception when provided."""
        original = ConnectionError("network down")
        error = BinaryDownloadError("failed", original_error=original)
        assert error.original_error is original

    def test_url_and_original_error_optional(self) -> None:
        """URL and original_error should be optional."""
        error = BinaryDownloadError("simple error")
        assert error.url is None
        assert error.original_error is None

    def test_all_attributes_together(self) -> None:
        """Error should handle all attributes at once."""
        original = TimeoutError("request timed out")
        error = BinaryDownloadError(
            message="Failed to download LiteFS binary",
            url="https://github.com/superfly/litefs/releases/download/v0.5.11/litefs-v0.5.11-linux-amd64.tar.gz",
            original_error=original,
        )
        assert error.message == "Failed to download LiteFS binary"
        assert "github.com" in error.url  # type: ignore[operator]
        assert error.original_error is original
        assert str(error) == "Failed to download LiteFS binary"
