"""Unit tests for mount path validation use case."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.mount_validator import MountValidator
from litefs.usecases.primary_detector import LiteFSNotRunningError


@pytest.mark.unit
class TestMountValidator:
    """Test mount path validation logic."""

    def test_validate_mount_path_exists(self):
        """Test that existing mount path passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            validator = MountValidator()
            # Should not raise
            validator.validate(mount_path)

    def test_validate_mount_path_raises_when_missing(self):
        """Test that missing mount path raises LiteFSNotRunningError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "nonexistent"
            validator = MountValidator()
            with pytest.raises(LiteFSNotRunningError) as exc_info:
                validator.validate(mount_path)
            assert "does not exist" in str(exc_info.value).lower() or "mount path" in str(exc_info.value).lower()

    def test_validate_mount_path_raises_when_not_absolute(self):
        """Test that relative paths raise error."""
        validator = MountValidator()
        relative_path = Path("relative/path")
        with pytest.raises(LiteFSConfigError) as exc_info:
            validator.validate(relative_path)
        assert "absolute" in str(exc_info.value).lower()

