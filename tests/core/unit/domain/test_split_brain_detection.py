"""Unit tests for split-brain detection domain value objects."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.split_brain import RaftNodeState, RaftClusterState
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestRaftNodeState:
    """Test RaftNodeState value object."""

    def test_create_with_node_id_and_is_leader(self) -> None:
        """Test creating RaftNodeState with node ID and leadership status."""
        state = RaftNodeState(node_id="node1", is_leader=True)
        assert state.node_id == "node1"
        assert state.is_leader is True

    def test_create_replica_node(self) -> None:
        """Test creating RaftNodeState for replica node."""
        state = RaftNodeState(node_id="node2", is_leader=False)
        assert state.node_id == "node2"
        assert state.is_leader is False

    def test_frozen_dataclass(self) -> None:
        """Test that RaftNodeState is immutable."""
        state = RaftNodeState(node_id="node1", is_leader=True)
        with pytest.raises(AttributeError):
            state.node_id = "node2"  # type: ignore

    def test_equality(self) -> None:
        """Test equality comparison for RaftNodeState."""
        state1 = RaftNodeState(node_id="node1", is_leader=True)
        state2 = RaftNodeState(node_id="node1", is_leader=True)
        assert state1 == state2

    def test_inequality_different_node_id(self) -> None:
        """Test inequality when node IDs differ."""
        state1 = RaftNodeState(node_id="node1", is_leader=True)
        state2 = RaftNodeState(node_id="node2", is_leader=True)
        assert state1 != state2

    def test_inequality_different_leadership_status(self) -> None:
        """Test inequality when leadership status differs."""
        state1 = RaftNodeState(node_id="node1", is_leader=True)
        state2 = RaftNodeState(node_id="node1", is_leader=False)
        assert state1 != state2

    def test_reject_empty_node_id(self) -> None:
        """Test that empty node ID is rejected."""
        with pytest.raises(LiteFSConfigError, match="node_id cannot be empty"):
            RaftNodeState(node_id="", is_leader=True)

    def test_reject_whitespace_only_node_id(self) -> None:
        """Test that whitespace-only node ID is rejected."""
        with pytest.raises(LiteFSConfigError, match="whitespace-only"):
            RaftNodeState(node_id="   ", is_leader=False)

    def test_hash_consistency(self) -> None:
        """Test that equal states have same hash."""
        state1 = RaftNodeState(node_id="node1", is_leader=True)
        state2 = RaftNodeState(node_id="node1", is_leader=True)
        assert hash(state1) == hash(state2)

    def test_can_use_in_set(self) -> None:
        """Test that RaftNodeState can be used in sets."""
        state1 = RaftNodeState(node_id="node1", is_leader=True)
        state2 = RaftNodeState(node_id="node1", is_leader=True)
        state3 = RaftNodeState(node_id="node2", is_leader=False)

        state_set = {state1, state2, state3}
        assert len(state_set) == 2  # state1 and state2 are equal


@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
class TestRaftNodeStatePBT:
    """Property-based tests for RaftNodeState."""

    @given(
        node_id=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=253,
        ),
        is_leader=st.booleans(),
    )
    def test_valid_node_states_accepted(self, node_id: str, is_leader: bool) -> None:
        """PBT: Valid node IDs should be accepted."""
        state = RaftNodeState(node_id=node_id, is_leader=is_leader)
        assert state.node_id == node_id
        assert state.is_leader == is_leader

    @given(is_leader=st.booleans())
    def test_whitespace_only_rejected(self, is_leader: bool) -> None:
        """PBT: Whitespace-only node IDs should be rejected."""
        with pytest.raises(LiteFSConfigError):
            RaftNodeState(node_id="   ", is_leader=is_leader)


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestRaftClusterState:
    """Test RaftClusterState value object."""

    def test_create_with_single_leader(self) -> None:
        """Test creating cluster state with single leader."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2])

        assert len(cluster.nodes) == 2
        assert cluster.has_single_leader() is True
        assert cluster.count_leaders() == 1

    def test_create_with_no_leaders(self) -> None:
        """Test creating cluster state with no leaders."""
        node1 = RaftNodeState(node_id="node1", is_leader=False)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2])

        assert len(cluster.nodes) == 2
        assert cluster.has_single_leader() is False
        assert cluster.count_leaders() == 0

    def test_create_with_multiple_leaders(self) -> None:
        """Test creating cluster state with multiple leaders (split-brain)."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=True)
        cluster = RaftClusterState(nodes=[node1, node2])

        assert len(cluster.nodes) == 2
        assert cluster.has_single_leader() is False
        assert cluster.count_leaders() == 2

    def test_get_leader_nodes_single_leader(self) -> None:
        """Test getting leader nodes when single leader exists."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2])

        leaders = cluster.get_leader_nodes()
        assert len(leaders) == 1
        assert leaders[0].node_id == "node1"

    def test_get_leader_nodes_multiple_leaders(self) -> None:
        """Test getting leader nodes when multiple leaders exist."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=True)
        node3 = RaftNodeState(node_id="node3", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2, node3])

        leaders = cluster.get_leader_nodes()
        assert len(leaders) == 2
        assert {n.node_id for n in leaders} == {"node1", "node2"}

    def test_get_leader_nodes_no_leaders(self) -> None:
        """Test getting leader nodes when no leaders exist."""
        node1 = RaftNodeState(node_id="node1", is_leader=False)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2])

        leaders = cluster.get_leader_nodes()
        assert len(leaders) == 0

    def test_get_replica_nodes(self) -> None:
        """Test getting replica nodes."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        node3 = RaftNodeState(node_id="node3", is_leader=False)
        cluster = RaftClusterState(nodes=[node1, node2, node3])

        replicas = cluster.get_replica_nodes()
        assert len(replicas) == 2
        assert {n.node_id for n in replicas} == {"node2", "node3"}

    def test_frozen_dataclass(self) -> None:
        """Test that RaftClusterState is immutable."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        cluster = RaftClusterState(nodes=[node1])

        with pytest.raises(AttributeError):
            cluster.nodes = []  # type: ignore

    def test_reject_empty_cluster(self) -> None:
        """Test that empty cluster is rejected."""
        with pytest.raises(LiteFSConfigError, match="cannot be empty"):
            RaftClusterState(nodes=[])

    def test_equality(self) -> None:
        """Test equality comparison for cluster states."""
        node1a = RaftNodeState(node_id="node1", is_leader=True)
        node2a = RaftNodeState(node_id="node2", is_leader=False)
        cluster1 = RaftClusterState(nodes=[node1a, node2a])

        node1b = RaftNodeState(node_id="node1", is_leader=True)
        node2b = RaftNodeState(node_id="node2", is_leader=False)
        cluster2 = RaftClusterState(nodes=[node1b, node2b])

        assert cluster1 == cluster2

    def test_inequality(self) -> None:
        """Test inequality when cluster states differ."""
        node1 = RaftNodeState(node_id="node1", is_leader=True)
        node2 = RaftNodeState(node_id="node2", is_leader=False)
        cluster1 = RaftClusterState(nodes=[node1, node2])

        node3 = RaftNodeState(node_id="node3", is_leader=False)
        cluster2 = RaftClusterState(nodes=[node1, node3])

        assert cluster1 != cluster2

    def test_three_node_cluster_with_single_leader(self) -> None:
        """Test 3-node cluster configuration."""
        nodes = [
            RaftNodeState(node_id="node1", is_leader=True),
            RaftNodeState(node_id="node2", is_leader=False),
            RaftNodeState(node_id="node3", is_leader=False),
        ]
        cluster = RaftClusterState(nodes=nodes)

        assert cluster.count_leaders() == 1
        assert cluster.has_single_leader() is True
        assert len(cluster.get_replica_nodes()) == 2

    def test_three_node_cluster_with_split_brain(self) -> None:
        """Test 3-node cluster with split-brain (2 leaders)."""
        nodes = [
            RaftNodeState(node_id="node1", is_leader=True),
            RaftNodeState(node_id="node2", is_leader=True),
            RaftNodeState(node_id="node3", is_leader=False),
        ]
        cluster = RaftClusterState(nodes=nodes)

        assert cluster.count_leaders() == 2
        assert cluster.has_single_leader() is False
        assert len(cluster.get_leader_nodes()) == 2

    def test_single_node_cluster(self) -> None:
        """Test single-node cluster configuration."""
        node = RaftNodeState(node_id="node1", is_leader=True)
        cluster = RaftClusterState(nodes=[node])

        assert cluster.count_leaders() == 1
        assert cluster.has_single_leader() is True
        assert len(cluster.get_replica_nodes()) == 0


@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
class TestRaftClusterStatePBT:
    """Property-based tests for RaftClusterState."""

    @given(
        leader_count=st.integers(min_value=0, max_value=5),
        replica_count=st.integers(min_value=1, max_value=5),
    )
    def test_leader_replica_counts_consistent(
        self, leader_count: int, replica_count: int
    ) -> None:
        """PBT: Leader and replica counts should sum to total nodes."""
        leaders = [
            RaftNodeState(node_id=f"leader{i}", is_leader=True)
            for i in range(leader_count)
        ]
        replicas = [
            RaftNodeState(node_id=f"replica{i}", is_leader=False)
            for i in range(replica_count)
        ]
        nodes = leaders + replicas

        if not nodes:
            return  # Skip empty cluster

        cluster = RaftClusterState(nodes=nodes)
        assert cluster.count_leaders() == leader_count
        assert len(cluster.get_replica_nodes()) == replica_count
        assert len(cluster.nodes) == leader_count + replica_count

    @given(
        leader_count=st.integers(min_value=0, max_value=5),
        replica_count=st.integers(min_value=1, max_value=5),
    )
    def test_has_single_leader_invariant(
        self, leader_count: int, replica_count: int
    ) -> None:
        """PBT: has_single_leader should match count_leaders == 1."""
        leaders = [
            RaftNodeState(node_id=f"leader{i}", is_leader=True)
            for i in range(leader_count)
        ]
        replicas = [
            RaftNodeState(node_id=f"replica{i}", is_leader=False)
            for i in range(replica_count)
        ]
        nodes = leaders + replicas

        cluster = RaftClusterState(nodes=nodes)
        assert cluster.has_single_leader() == (cluster.count_leaders() == 1)

    @given(
        leader_count=st.integers(min_value=0, max_value=3),
        replica_count=st.integers(min_value=1, max_value=3),
    )
    def test_leader_node_list_consistency(
        self, leader_count: int, replica_count: int
    ) -> None:
        """PBT: get_leader_nodes should return exactly count_leaders items."""
        leaders = [
            RaftNodeState(node_id=f"leader{i}", is_leader=True)
            for i in range(leader_count)
        ]
        replicas = [
            RaftNodeState(node_id=f"replica{i}", is_leader=False)
            for i in range(replica_count)
        ]
        nodes = leaders + replicas

        cluster = RaftClusterState(nodes=nodes)
        assert len(cluster.get_leader_nodes()) == cluster.count_leaders()
        assert len(cluster.get_leader_nodes()) == leader_count
