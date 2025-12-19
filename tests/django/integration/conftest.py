"""Pytest fixtures for Django LiteFS integration tests."""

import os
import platform
import subprocess

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires Docker + FUSE)"
    )


def _check_fuse_available():
    """Check if FUSE is available on the current platform.

    Returns:
        True if FUSE is available or on non-POSIX systems (fallback).
    """
    if os.name != "posix":
        # Non-POSIX systems (Windows) - assume FUSE available via fallback
        return True

    # POSIX systems - check platform-specific FUSE paths
    if platform.system() == "Darwin":
        # macOS uses osxfuse or macfuse
        return os.path.exists("/dev/osxfuse") or os.path.exists("/dev/macfuse")
    else:
        # Linux and other POSIX systems use /dev/fuse
        return os.path.exists("/dev/fuse")


@pytest.fixture
def litefs_available():
    """Check if LiteFS/FUSE is available for integration tests.

    Returns True if LiteFS infrastructure is available, False otherwise.
    Integration tests should skip if this returns False.

    Thread-safe implementation using subprocess.run instead of os.system.
    """
    # Check for Docker availability (thread-safe)
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5,
        )
        docker_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        docker_available = False

    # Check for FUSE availability (cross-platform)
    fuse_available = _check_fuse_available()

    return docker_available and fuse_available


@pytest.fixture
def skip_if_no_litefs(litefs_available):
    """Fixture that skips test if LiteFS infrastructure is not available."""
    if not litefs_available:
        pytest.skip("LiteFS infrastructure (Docker/FUSE) not available")

