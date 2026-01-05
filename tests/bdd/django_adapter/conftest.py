"""Shared fixtures for Django adapter BDD tests."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs.domain.split_brain import RaftClusterState, RaftNodeState  # noqa: E402
from tests.django_adapter.unit.fakes import FakePrimaryDetector, FakeSplitBrainDetector  # noqa: E402

if TYPE_CHECKING:
    pass


@pytest.fixture
def context() -> dict:
    """Shared context for passing state between steps."""
    return {}


@pytest.fixture
def fake_primary_detector() -> FakePrimaryDetector:
    """Create a fake primary detector for testing."""
    return FakePrimaryDetector(is_primary=True)


@pytest.fixture
def fake_split_brain_detector() -> FakeSplitBrainDetector:
    """Create a fake split-brain detector for testing.

    Default: healthy cluster with single leader (no split-brain).
    """
    return FakeSplitBrainDetector()


@pytest.fixture
def in_memory_connection() -> sqlite3.Connection:
    """Create an in-memory SQLite connection for cursor testing."""
    conn = sqlite3.connect(":memory:")
    # Create a test table for SQL execution
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    return conn


def create_split_brain_cluster(leader_count: int) -> RaftClusterState:
    """Create a cluster state with the specified number of leaders.

    Args:
        leader_count: Number of nodes that claim leadership.

    Returns:
        RaftClusterState with the specified number of leaders.
    """
    nodes = []
    for i in range(max(leader_count, 3)):
        is_leader = i < leader_count
        nodes.append(RaftNodeState(node_id=f"node{i + 1}", is_leader=is_leader))
    return RaftClusterState(nodes=nodes)


def create_healthy_cluster() -> RaftClusterState:
    """Create a healthy cluster state with single leader."""
    return create_split_brain_cluster(leader_count=1)
