"""Shared fixtures for BDD tests."""

import pytest
from pathlib import Path


@pytest.fixture
def mount_path(tmp_path: Path) -> Path:
    """Create a temporary mount path for testing.

    Returns:
        Path to temporary directory simulating LiteFS mount.
    """
    litefs_mount = tmp_path / "litefs"
    litefs_mount.mkdir()
    return litefs_mount


@pytest.fixture
def nonexistent_mount_path(tmp_path: Path) -> Path:
    """Return a path that does not exist.

    Returns:
        Path that does not exist (for error testing).
    """
    return tmp_path / "nonexistent"
