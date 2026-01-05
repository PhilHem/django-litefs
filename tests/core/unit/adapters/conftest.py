"""Pytest configuration for core adapter unit tests."""

import pytest

from .adapter_fakes import FakeHttpxClient, FakeRaftLeaderElection


@pytest.fixture
def fake_raft_election():
    """Provide FakeRaftLeaderElection for unit tests.

    Use instead of real RaftLeaderElection for faster tests without
    PySyncObj dependency.

    Example:
        def test_split_brain_detection(fake_raft_election):
            fake_raft_election.set_leader(True)
            fake_raft_election.set_cluster_members(["node1:20202", "node2:20202"])
    """
    return FakeRaftLeaderElection()


@pytest.fixture
def fake_httpx_client():
    """Provide FakeHttpxClient for unit tests.

    Use instead of real httpx.Client for faster tests without network I/O.

    Example:
        def test_remote_node_query(fake_httpx_client):
            fake_httpx_client.add_response(
                "http://node2:8080/health/status",
                {"is_leader": True}
            )
    """
    return FakeHttpxClient()
