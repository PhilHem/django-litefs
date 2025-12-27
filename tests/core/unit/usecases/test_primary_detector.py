"""Unit tests for PrimaryDetector use case."""

import pytest
from pathlib import Path

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestPrimaryDetector:
    """Test PrimaryDetector use case."""

    def test_detect_primary_when_file_exists(self, tmp_path):
        """Test detecting primary when .primary file exists."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        detector = PrimaryDetector(mount_path=str(mount_path))
        assert detector.is_primary() is True

    def test_detect_replica_when_file_does_not_exist(self, tmp_path):
        """Test detecting replica when .primary file does not exist."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        detector = PrimaryDetector(mount_path=str(mount_path))
        assert detector.is_primary() is False

    def test_raise_error_when_mount_path_does_not_exist(self):
        """Test that error is raised when mount path doesn't exist."""
        detector = PrimaryDetector(mount_path="/nonexistent/path")
        with pytest.raises(LiteFSNotRunningError):
            detector.is_primary()

    def test_is_litefs_running_returns_true_when_mount_path_exists(self, tmp_path):
        """Test is_litefs_running returns True when mount path exists."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        detector = PrimaryDetector(mount_path=str(mount_path))
        assert detector.is_litefs_running() is True

    def test_is_litefs_running_returns_false_when_mount_path_does_not_exist(self):
        """Test is_litefs_running returns False when mount path doesn't exist."""
        detector = PrimaryDetector(mount_path="/nonexistent/path")
        assert detector.is_litefs_running() is False
