"""Unit tests for PrimaryURLDetector use case."""

import pytest

from litefs.usecases.primary_url_detector import PrimaryURLDetector


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLDetector")
class TestPrimaryURLDetector:
    """Test PrimaryURLDetector use case."""

    def test_returns_none_when_file_missing(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that None is returned when .primary file doesn't exist."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        detector = PrimaryURLDetector(mount_path=str(mount_path))
        assert detector.get_primary_url() is None

    def test_returns_empty_string_when_file_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that empty string is returned when .primary file is empty (this node is primary)."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("")

        detector = PrimaryURLDetector(mount_path=str(mount_path))
        assert detector.get_primary_url() == ""

    def test_returns_url_when_file_has_content(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that URL is returned when .primary file has content."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("primary.local:8080")

        detector = PrimaryURLDetector(mount_path=str(mount_path))
        assert detector.get_primary_url() == "primary.local:8080"

    def test_strips_whitespace_from_url(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that whitespace is stripped from URL content."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("  primary.local:8080\n")

        detector = PrimaryURLDetector(mount_path=str(mount_path))
        assert detector.get_primary_url() == "primary.local:8080"

    def test_handles_url_with_port(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test handling of URL with various port formats."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("192.168.1.100:20202")

        detector = PrimaryURLDetector(mount_path=str(mount_path))
        assert detector.get_primary_url() == "192.168.1.100:20202"
