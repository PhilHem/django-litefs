"""Unit tests for SplitBrainDetectorAdapter."""

from __future__ import annotations

import httpx
import pytest

from litefs.adapters.ports import SplitBrainDetectorPort
from litefs.adapters.split_brain_detector_adapter import SplitBrainDetectorAdapter
from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from .adapter_fakes import FakeHttpxClient, FakeRaftLeaderElection


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterProtocolCompliance:
    """Test that SplitBrainDetectorAdapter implements port protocol correctly."""

    def test_adapter_satisfies_split_brain_detector_port(self) -> None:
        """Test that adapter satisfies SplitBrainDetectorPort protocol."""
        fake_raft = FakeRaftLeaderElection()
        fake_client = FakeHttpxClient()
        fake_client.set_default_response({"is_leader": False})

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )
        assert isinstance(adapter, SplitBrainDetectorPort)

    def test_adapter_has_get_cluster_state_method(self) -> None:
        """Test that adapter has get_cluster_state method."""
        fake_raft = FakeRaftLeaderElection()
        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )
        assert hasattr(adapter, "get_cluster_state")
        assert callable(adapter.get_cluster_state)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterConstructor:
    """Test SplitBrainDetectorAdapter constructor and initialization."""

    def test_constructor_accepts_required_parameters(self) -> None:
        """Test that constructor accepts required parameters."""
        fake_raft = FakeRaftLeaderElection()
        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )
        assert adapter is not None

    def test_constructor_accepts_optional_parameters(self) -> None:
        """Test that constructor accepts optional parameters."""
        fake_raft = FakeRaftLeaderElection()
        fake_client = FakeHttpxClient()

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            health_endpoint_path="/custom/health",
            health_endpoint_port=9090,
            connect_timeout=1.0,
            read_timeout=2.0,
            client=fake_client,
        )
        assert adapter is not None

    def test_constructor_stores_this_node_id(self) -> None:
        """Test that constructor stores this_node_id."""
        fake_raft = FakeRaftLeaderElection()
        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="my-node",
        )
        assert adapter._this_node_id == "my-node"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterLocalNode:
    """Test that adapter uses local Raft state for this node."""

    def test_local_node_uses_raft_leader_state_when_leader(self) -> None:
        """Test that local node leadership comes from Raft, not HTTP."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202"],
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )

        state = adapter.get_cluster_state()

        assert len(state.nodes) == 1
        assert state.nodes[0].node_id == "node1"
        assert state.nodes[0].is_leader is True

    def test_local_node_uses_raft_leader_state_when_not_leader(self) -> None:
        """Test that local node non-leadership comes from Raft."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=False,
            cluster_members=["node1:20202"],
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )

        state = adapter.get_cluster_state()

        assert len(state.nodes) == 1
        assert state.nodes[0].node_id == "node1"
        assert state.nodes[0].is_leader is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterRemoteNodes:
    """Test that adapter queries remote nodes via HTTP."""

    def test_queries_remote_node_health_endpoint(self) -> None:
        """Test that remote nodes are queried via HTTP."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            {"is_leader": False},
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        assert len(state.nodes) == 2
        # Check that HTTP request was made
        assert "http://node2:8080/health/status" in fake_client.requests_made
        # Check remote node state
        node2_state = next(n for n in state.nodes if n.node_id == "node2")
        assert node2_state.is_leader is False

    def test_remote_node_leader_detected(self) -> None:
        """Test that remote node leadership is correctly detected."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=False,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            {"is_leader": True},
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        node2_state = next(n for n in state.nodes if n.node_id == "node2")
        assert node2_state.is_leader is True

    def test_uses_custom_health_endpoint_port(self) -> None:
        """Test that custom health endpoint port is used."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:9000/health/status",
            {"is_leader": False},
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            health_endpoint_port=9000,
            client=fake_client,
        )

        adapter.get_cluster_state()

        assert "http://node2:9000/health/status" in fake_client.requests_made

    def test_uses_custom_health_endpoint_path(self) -> None:
        """Test that custom health endpoint path is used."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/custom/health",
            {"is_leader": False},
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            health_endpoint_path="/custom/health",
            client=fake_client,
        )

        adapter.get_cluster_state()

        assert "http://node2:8080/custom/health" in fake_client.requests_made


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterErrorHandling:
    """Test error handling for unreachable or failing nodes."""

    def test_unreachable_node_treated_as_non_leader(self) -> None:
        """Test that unreachable nodes are treated as non-leaders."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            error=httpx.ConnectError("Connection refused"),
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        node2_state = next(n for n in state.nodes if n.node_id == "node2")
        assert node2_state.is_leader is False

    def test_http_error_treated_as_non_leader(self) -> None:
        """Test that HTTP errors result in non-leader status."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            status_code=500,
            json_data=None,
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        node2_state = next(n for n in state.nodes if n.node_id == "node2")
        assert node2_state.is_leader is False

    def test_invalid_json_treated_as_non_leader(self) -> None:
        """Test that invalid JSON responses result in non-leader status."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            json_data=None,  # Will raise ValueError on .json() call
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        node2_state = next(n for n in state.nodes if n.node_id == "node2")
        assert node2_state.is_leader is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterMultiNode:
    """Test multi-node cluster scenarios."""

    def test_three_node_cluster_healthy(self) -> None:
        """Test healthy 3-node cluster with single leader."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,
            cluster_members=["node1:20202", "node2:20202", "node3:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status", {"is_leader": False}
        )
        fake_client.add_response(
            "http://node3:8080/health/status", {"is_leader": False}
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        assert len(state.nodes) == 3
        assert state.has_single_leader() is True
        assert state.count_leaders() == 1

    def test_split_brain_detected(self) -> None:
        """Test split-brain detection when multiple nodes claim leadership."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=True,  # This node thinks it's leader
            cluster_members=["node1:20202", "node2:20202", "node3:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status",
            {"is_leader": True},  # Split brain!
        )
        fake_client.add_response(
            "http://node3:8080/health/status", {"is_leader": False}
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        assert state.has_single_leader() is False
        assert state.count_leaders() == 2
        leaders = state.get_leader_nodes()
        leader_ids = [n.node_id for n in leaders]
        assert "node1" in leader_ids
        assert "node2" in leader_ids

    def test_no_leader_cluster(self) -> None:
        """Test cluster with no leaders."""
        fake_raft = FakeRaftLeaderElection(
            is_leader=False,
            cluster_members=["node1:20202", "node2:20202", "node3:20202"],
        )
        fake_client = FakeHttpxClient()
        fake_client.add_response(
            "http://node2:8080/health/status", {"is_leader": False}
        )
        fake_client.add_response(
            "http://node3:8080/health/status", {"is_leader": False}
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
            client=fake_client,
        )

        state = adapter.get_cluster_state()

        assert state.count_leaders() == 0
        assert state.has_single_leader() is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.SplitBrainDetector")
class TestSplitBrainDetectorAdapterReturnType:
    """Test that get_cluster_state returns correct types."""

    def test_returns_raft_cluster_state(self) -> None:
        """Test that get_cluster_state returns RaftClusterState."""
        fake_raft = FakeRaftLeaderElection(
            cluster_members=["node1:20202"],
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )

        state = adapter.get_cluster_state()

        assert isinstance(state, RaftClusterState)

    def test_nodes_are_raft_node_state(self) -> None:
        """Test that nodes in cluster state are RaftNodeState."""
        fake_raft = FakeRaftLeaderElection(
            cluster_members=["node1:20202"],
        )

        adapter = SplitBrainDetectorAdapter(
            raft_election=fake_raft,
            this_node_id="node1",
        )

        state = adapter.get_cluster_state()

        for node in state.nodes:
            assert isinstance(node, RaftNodeState)
