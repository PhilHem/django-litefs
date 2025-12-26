"""Pytest fixtures for Django LiteFS integration tests."""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any

import pytest


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires Docker + FUSE)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests with Docker Compose cluster"
    )
    config.addinivalue_line(
        "markers", "tier(level): Test tier (0=instant, 1=fast, 2=standard, 3=slow, 4=manual)"
    )
    config.addinivalue_line(
        "markers", "tra(anchor): Test Responsibility Anchor"
    )
    config.addinivalue_line(
        "markers", "legacy: Legacy tests without TRA marker (being migrated)"
    )
    config.addinivalue_line(
        "markers", "no_parallel: Tests that cannot run in parallel (shared state/filesystem)"
    )


def _check_fuse_available() -> bool:
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
def litefs_available() -> bool:
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
def skip_if_no_litefs(litefs_available: bool) -> None:
    """Fixture that skips test if LiteFS infrastructure is not available."""
    if not litefs_available:
        pytest.skip("LiteFS infrastructure (Docker/FUSE) not available")


@pytest.fixture
def docker_compose_cluster(litefs_available: bool) -> Any:
    """Fixture providing a Docker Compose LiteFS cluster for integration tests.

    This fixture manages the lifecycle of a 3-node LiteFS cluster running
    in Docker Compose. Each node has:
    - LiteFS binary configured for Raft-based leader election
    - SQLite database for replication
    - Network connectivity to other nodes

    The fixture:
    1. Starts docker-compose cluster
    2. Waits for cluster to reach healthy state (all nodes reporting)
    3. Yields cluster reference to test
    4. Cleans up cluster on test completion

    Tests should use this fixture to run Docker Compose scenarios.
    The fixture handles the complexity of cluster lifecycle management.

    Usage:
        def test_something(docker_compose_cluster):
            # docker_compose_cluster provides cluster reference
            pytest.skip("Implementation pending")
    """
    if not litefs_available:
        pytest.skip("Docker/FUSE not available for cluster tests")

    # Placeholder: Docker Compose cluster fixture
    # Implementation pending - requires docker-compose.yml in tests/django_adapter/integration/
    # and cluster management code
    pytest.skip("Docker Compose cluster fixture implementation pending")


@pytest.fixture
def cluster_state_monitor(docker_compose_cluster: Any) -> Any:
    """Fixture providing cluster state monitoring for integration tests.

    This fixture wraps the docker_compose_cluster and provides methods to:
    - Query current leader from cluster
    - List all nodes and their states
    - Detect split-brain conditions
    - Verify replication status
    - Create network partitions (disconnect containers)
    - Heal network partitions (reconnect containers)

    Tests should use this fixture to interact with cluster state.

    Usage:
        def test_partition(cluster_state_monitor):
            leader = cluster_state_monitor.get_leader()
            pytest.skip("Implementation pending")
    """
    pytest.skip("Cluster state monitor fixture implementation pending")
