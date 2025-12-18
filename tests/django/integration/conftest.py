"""Pytest fixtures for Django LiteFS integration tests."""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires Docker + FUSE)"
    )


@pytest.fixture
def litefs_available():
    """Check if LiteFS/FUSE is available for integration tests.

    Returns True if LiteFS infrastructure is available, False otherwise.
    Integration tests should skip if this returns False.
    """
    # Check for Docker availability
    docker_available = os.system("docker --version > /dev/null 2>&1") == 0

    # Check for FUSE availability (simplified check)
    # In a real implementation, this would check for FUSE support
    fuse_available = os.path.exists("/dev/fuse") or os.name != "posix"

    return docker_available and fuse_available


@pytest.fixture
def skip_if_no_litefs(litefs_available):
    """Fixture that skips test if LiteFS infrastructure is not available."""
    if not litefs_available:
        pytest.skip("LiteFS infrastructure (Docker/FUSE) not available")
