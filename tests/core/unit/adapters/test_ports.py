"""Unit tests for port interfaces and default implementations."""

import os
import pytest
from hypothesis import given, strategies as st, settings

from litefs.adapters.ports import (
    NodeIDResolverPort,
    EnvironmentNodeIDResolver,
    LeaderElectionPort,
    RaftLeaderElectionPort,
    SplitBrainDetectorPort,
)
from litefs.domain.split_brain import RaftClusterState, RaftNodeState


@pytest.mark.unit
class TestNodeIDResolverPort:
    """Test NodeIDResolverPort protocol interface."""

    def test_protocol_has_resolve_node_id_method(self) -> None:
        """Test that NodeIDResolverPort has resolve_node_id method."""
        assert hasattr(NodeIDResolverPort, "resolve_node_id")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that NodeIDResolverPort is runtime_checkable."""

        # Create a simple object that implements the protocol
        class FakeResolver:
            def resolve_node_id(self) -> str:
                return "fake-node"

        fake = FakeResolver()
        # If runtime_checkable works, isinstance should return True
        assert isinstance(fake, NodeIDResolverPort)


@pytest.mark.unit
class TestEnvironmentNodeIDResolver:
    """Test EnvironmentNodeIDResolver implementation."""

    def test_resolve_from_environment_variable(self) -> None:
        """Test resolving node ID from LITEFS_NODE_ID environment variable."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-1"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_resolve_with_fqdn_hostname(self) -> None:
        """Test resolving FQDN hostname from environment."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "app-server-01.example.com"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "app-server-01.example.com"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_raise_on_missing_environment_variable(self) -> None:
        """Test that KeyError is raised when LITEFS_NODE_ID is not set."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ.pop("LITEFS_NODE_ID", None)
            resolver = EnvironmentNodeIDResolver()
            with pytest.raises(KeyError, match="LITEFS_NODE_ID"):
                resolver.resolve_node_id()
        finally:
            if original is not None:
                os.environ["LITEFS_NODE_ID"] = original

    def test_strips_leading_whitespace(self) -> None:
        """Test that leading whitespace is stripped from node ID."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "  node-1"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_strips_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is stripped from node ID."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-1  "
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_rejects_whitespace_only_value(self) -> None:
        """Test that whitespace-only node ID is rejected."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "   "
            resolver = EnvironmentNodeIDResolver()
            with pytest.raises(ValueError, match="node ID cannot be empty"):
                resolver.resolve_node_id()
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_satisfies_protocol(self) -> None:
        """Test that EnvironmentNodeIDResolver satisfies NodeIDResolverPort protocol."""
        resolver = EnvironmentNodeIDResolver()
        assert isinstance(resolver, NodeIDResolverPort)


@pytest.mark.unit
class TestProtocolImplementationContract:
    """Test contract between protocol and implementations."""

    def test_environment_resolver_returns_string(self) -> None:
        """Test that EnvironmentNodeIDResolver.resolve_node_id() returns str."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "test-node"
            resolver = EnvironmentNodeIDResolver()
            result = resolver.resolve_node_id()
            assert isinstance(result, str)
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_environment_resolver_never_returns_empty_string(self) -> None:
        """Test that resolve_node_id() never returns empty string."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-123"
            resolver = EnvironmentNodeIDResolver()
            result = resolver.resolve_node_id()
            assert result != ""
            assert len(result) > 0
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original


@pytest.mark.unit
class TestLeaderElectionPort:
    """Test LeaderElectionPort protocol interface."""

    def test_protocol_has_required_methods(self) -> None:
        """Test that LeaderElectionPort has all required methods."""
        assert hasattr(LeaderElectionPort, "is_leader_elected")
        assert hasattr(LeaderElectionPort, "elect_as_leader")
        assert hasattr(LeaderElectionPort, "demote_from_leader")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that LeaderElectionPort is runtime_checkable."""

        class FakeElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

        fake = FakeElection()
        assert isinstance(fake, LeaderElectionPort)


@pytest.mark.unit
class TestRaftLeaderElectionPort:
    """Test RaftLeaderElectionPort protocol interface."""

    def test_protocol_extends_leader_election_port(self) -> None:
        """Test that RaftLeaderElectionPort has all LeaderElectionPort methods."""
        assert hasattr(RaftLeaderElectionPort, "is_leader_elected")
        assert hasattr(RaftLeaderElectionPort, "elect_as_leader")
        assert hasattr(RaftLeaderElectionPort, "demote_from_leader")

    def test_protocol_has_raft_specific_methods(self) -> None:
        """Test that RaftLeaderElectionPort has Raft-specific methods."""
        assert hasattr(RaftLeaderElectionPort, "get_cluster_members")
        assert hasattr(RaftLeaderElectionPort, "is_member_in_cluster")
        assert hasattr(RaftLeaderElectionPort, "get_election_timeout")
        assert hasattr(RaftLeaderElectionPort, "get_heartbeat_interval")
        assert hasattr(RaftLeaderElectionPort, "is_quorum_reached")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that RaftLeaderElectionPort is runtime_checkable."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return []

            def is_member_in_cluster(self, node_id: str) -> bool:
                return False

            def get_election_timeout(self) -> float:
                return 1.0

            def get_heartbeat_interval(self) -> float:
                return 0.5

            def is_quorum_reached(self) -> bool:
                return False

        fake = FakeRaftElection()
        assert isinstance(fake, RaftLeaderElectionPort)

    def test_get_cluster_members_returns_empty_list(self) -> None:
        """Test that get_cluster_members can return empty list."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return []

            def is_member_in_cluster(self, node_id: str) -> bool:
                return False

            def get_election_timeout(self) -> float:
                return 1.0

            def get_heartbeat_interval(self) -> float:
                return 0.5

            def is_quorum_reached(self) -> bool:
                return False

        election = FakeRaftElection()
        assert isinstance(election, RaftLeaderElectionPort)
        members = election.get_cluster_members()
        assert isinstance(members, list)
        assert len(members) == 0

    def test_get_cluster_members_returns_list_of_strings(self) -> None:
        """Test that get_cluster_members returns list of strings."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return ["node-1", "node-2", "node-3"]

            def is_member_in_cluster(self, node_id: str) -> bool:
                return node_id in self.get_cluster_members()

            def get_election_timeout(self) -> float:
                return 1.0

            def get_heartbeat_interval(self) -> float:
                return 0.5

            def is_quorum_reached(self) -> bool:
                return True

        election = FakeRaftElection()
        members = election.get_cluster_members()
        assert all(isinstance(m, str) for m in members)
        assert len(members) == 3

    def test_is_member_in_cluster_with_existing_member(self) -> None:
        """Test is_member_in_cluster with existing member."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return ["node-1", "node-2"]

            def is_member_in_cluster(self, node_id: str) -> bool:
                return node_id in ["node-1", "node-2"]

            def get_election_timeout(self) -> float:
                return 1.0

            def get_heartbeat_interval(self) -> float:
                return 0.5

            def is_quorum_reached(self) -> bool:
                return True

        election = FakeRaftElection()
        assert election.is_member_in_cluster("node-1") is True

    def test_is_member_in_cluster_with_nonexistent_member(self) -> None:
        """Test is_member_in_cluster with non-existent member."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return ["node-1", "node-2"]

            def is_member_in_cluster(self, node_id: str) -> bool:
                return node_id in ["node-1", "node-2"]

            def get_election_timeout(self) -> float:
                return 1.0

            def get_heartbeat_interval(self) -> float:
                return 0.5

            def is_quorum_reached(self) -> bool:
                return True

        election = FakeRaftElection()
        assert election.is_member_in_cluster("node-3") is False

    def test_get_election_timeout_returns_positive_float(self) -> None:
        """Test that get_election_timeout returns positive float."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return []

            def is_member_in_cluster(self, node_id: str) -> bool:
                return False

            def get_election_timeout(self) -> float:
                return 5.0

            def get_heartbeat_interval(self) -> float:
                return 1.0

            def is_quorum_reached(self) -> bool:
                return False

        election = FakeRaftElection()
        timeout = election.get_election_timeout()
        assert isinstance(timeout, float)
        assert timeout > 0

    def test_get_heartbeat_interval_returns_positive_float(self) -> None:
        """Test that get_heartbeat_interval returns positive float."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return []

            def is_member_in_cluster(self, node_id: str) -> bool:
                return False

            def get_election_timeout(self) -> float:
                return 5.0

            def get_heartbeat_interval(self) -> float:
                return 1.0

            def is_quorum_reached(self) -> bool:
                return False

        election = FakeRaftElection()
        interval = election.get_heartbeat_interval()
        assert isinstance(interval, float)
        assert interval > 0

    def test_is_quorum_reached_returns_bool(self) -> None:
        """Test that is_quorum_reached returns bool."""

        class FakeRaftElection:
            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return ["node-1", "node-2", "node-3"]

            def is_member_in_cluster(self, node_id: str) -> bool:
                return node_id in self.get_cluster_members()

            def get_election_timeout(self) -> float:
                return 5.0

            def get_heartbeat_interval(self) -> float:
                return 1.0

            def is_quorum_reached(self) -> bool:
                return True

        election = FakeRaftElection()
        quorum = election.is_quorum_reached()
        assert isinstance(quorum, bool)

    @pytest.mark.property
    @given(cluster_size=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_quorum_invariant_majority_quorum(self, cluster_size: int) -> None:
        """Test quorum invariant: quorum requires > n/2 nodes.

        Property: For a cluster of size n, quorum is reached with > n/2 nodes.
        This property tests the mathematical invariant of Raft consensus.
        """

        class TestRaftElection:
            def __init__(self, cluster_size: int, online_count: int):
                self.cluster_size = cluster_size
                self.online_count = online_count
                self._members = [f"node-{i}" for i in range(cluster_size)]

            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return self._members

            def is_member_in_cluster(self, node_id: str) -> bool:
                return node_id in self._members

            def get_election_timeout(self) -> float:
                return 5.0

            def get_heartbeat_interval(self) -> float:
                return 1.0

            def is_quorum_reached(self) -> bool:
                required_quorum = (self.cluster_size // 2) + 1
                return self.online_count >= required_quorum

        # Test with different online node counts
        quorum_threshold = (cluster_size // 2) + 1

        # Below quorum should return False
        election_below = TestRaftElection(cluster_size, quorum_threshold - 1)
        assert election_below.is_quorum_reached() is False

        # At quorum should return True
        election_at = TestRaftElection(cluster_size, quorum_threshold)
        assert election_at.is_quorum_reached() is True

        # Above quorum should return True
        if quorum_threshold < cluster_size:
            election_above = TestRaftElection(cluster_size, quorum_threshold + 1)
            assert election_above.is_quorum_reached() is True

    @pytest.mark.property
    @given(timeout_val=st.floats(min_value=0.1, max_value=10.0))
    @settings(max_examples=50)
    def test_timing_invariant_heartbeat_less_than_timeout(
        self, timeout_val: float
    ) -> None:
        """Test timing invariant: heartbeat_interval < election_timeout.

        Property: In Raft, heartbeat interval must be less than election timeout
        to allow proper consensus without triggering unnecessary elections.
        """

        class TestRaftElection:
            def __init__(self, election_timeout: float):
                self.election_timeout = election_timeout

            def is_leader_elected(self) -> bool:
                return False

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

            def get_cluster_members(self) -> list[str]:
                return ["node-1", "node-2"]

            def is_member_in_cluster(self, node_id: str) -> bool:
                return True

            def get_election_timeout(self) -> float:
                return self.election_timeout

            def get_heartbeat_interval(self) -> float:
                return self.election_timeout / 3.0

            def is_quorum_reached(self) -> bool:
                return True

        election = TestRaftElection(timeout_val)
        heartbeat = election.get_heartbeat_interval()
        election_timeout = election.get_election_timeout()

        # Invariant: heartbeat must be less than election timeout
        assert heartbeat < election_timeout


@pytest.mark.unit
class TestSplitBrainDetectorPort:
    """Test SplitBrainDetectorPort protocol interface."""

    def test_protocol_has_get_cluster_state_method(self) -> None:
        """Test that SplitBrainDetectorPort has get_cluster_state method."""
        assert hasattr(SplitBrainDetectorPort, "get_cluster_state")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that SplitBrainDetectorPort is runtime_checkable."""

        class FakeSplitBrainDetector:
            def get_cluster_state(self) -> RaftClusterState:
                return RaftClusterState(
                    nodes=[RaftNodeState(node_id="node-1", is_leader=True)]
                )

        fake = FakeSplitBrainDetector()
        # If runtime_checkable works, isinstance should return True
        assert isinstance(fake, SplitBrainDetectorPort)

    def test_mock_implementation_satisfies_protocol(self) -> None:
        """Test that a mock implementation satisfies the protocol."""

        class MockDetector:
            def get_cluster_state(self) -> RaftClusterState:
                return RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node-1", is_leader=True),
                        RaftNodeState(node_id="node-2", is_leader=False),
                    ]
                )

        mock = MockDetector()
        assert isinstance(mock, SplitBrainDetectorPort)
        state = mock.get_cluster_state()
        assert isinstance(state, RaftClusterState)

    def test_contract_get_cluster_state_returns_raft_cluster_state(self) -> None:
        """Test that get_cluster_state() returns RaftClusterState."""

        class TestDetector:
            def get_cluster_state(self) -> RaftClusterState:
                return RaftClusterState(
                    nodes=[RaftNodeState(node_id="test-node", is_leader=True)]
                )

        detector = TestDetector()
        state = detector.get_cluster_state()

        assert isinstance(state, RaftClusterState)
        assert hasattr(state, "nodes")
        assert isinstance(state.nodes, list)

    def test_get_cluster_state_single_leader(self) -> None:
        """Test get_cluster_state with healthy cluster (single leader)."""

        class HealthyDetector:
            def get_cluster_state(self) -> RaftClusterState:
                return RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node-1", is_leader=True),
                        RaftNodeState(node_id="node-2", is_leader=False),
                        RaftNodeState(node_id="node-3", is_leader=False),
                    ]
                )

        detector = HealthyDetector()
        assert isinstance(detector, SplitBrainDetectorPort)

        state = detector.get_cluster_state()
        assert state.count_leaders() == 1
        assert state.has_single_leader() is True
        assert len(state.nodes) == 3

    def test_get_cluster_state_multiple_leaders_split_brain(self) -> None:
        """Test get_cluster_state detecting split-brain (multiple leaders)."""

        class SplitBrainDetector:
            def get_cluster_state(self) -> RaftClusterState:
                # Simulate split-brain: two nodes think they're leaders
                return RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node-1", is_leader=True),
                        RaftNodeState(node_id="node-2", is_leader=True),
                        RaftNodeState(node_id="node-3", is_leader=False),
                    ]
                )

        detector = SplitBrainDetector()
        assert isinstance(detector, SplitBrainDetectorPort)

        state = detector.get_cluster_state()
        assert state.count_leaders() == 2
        assert state.has_single_leader() is False
        leader_nodes = state.get_leader_nodes()
        assert len(leader_nodes) == 2
        assert all(node.is_leader for node in leader_nodes)

    def test_get_cluster_state_no_leaders(self) -> None:
        """Test get_cluster_state edge case with no leaders."""

        class NoLeaderDetector:
            def get_cluster_state(self) -> RaftClusterState:
                # All nodes are replicas, no leader (cluster issue)
                return RaftClusterState(
                    nodes=[
                        RaftNodeState(node_id="node-1", is_leader=False),
                        RaftNodeState(node_id="node-2", is_leader=False),
                        RaftNodeState(node_id="node-3", is_leader=False),
                    ]
                )

        detector = NoLeaderDetector()
        assert isinstance(detector, SplitBrainDetectorPort)

        state = detector.get_cluster_state()
        assert state.count_leaders() == 0
        assert state.has_single_leader() is False
        assert len(state.get_leader_nodes()) == 0
        assert len(state.get_replica_nodes()) == 3
