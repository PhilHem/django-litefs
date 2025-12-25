"""Unit tests for RaftLeaderElection implementation.

Tests verify that RaftLeaderElection correctly implements the RaftLeaderElectionPort
interface and handles Raft-specific cluster management operations.
"""

import pytest
from hypothesis import given, strategies as st, settings

from py_leader import RaftLeaderElection


@pytest.mark.unit
class TestRaftLeaderElectionInitialization:
    """Test RaftLeaderElection initialization and validation."""

    def test_initialize_with_valid_parameters(self) -> None:
        """Test initialization with valid parameters."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.get_cluster_members() == ["node-1", "node-2", "node-3"]
        assert election.get_election_timeout() == 5.0
        assert election.get_heartbeat_interval() == 1.0

    def test_initialize_with_single_node_cluster(self) -> None:
        """Test initialization with single-node cluster."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.get_cluster_members() == ["node-1"]

    def test_raise_on_negative_heartbeat_interval(self) -> None:
        """Test that negative heartbeat_interval raises ValueError."""
        with pytest.raises(ValueError, match="heartbeat_interval must be > 0"):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=5.0,
                heartbeat_interval=-1.0,
            )

    def test_raise_on_zero_heartbeat_interval(self) -> None:
        """Test that zero heartbeat_interval raises ValueError."""
        with pytest.raises(ValueError, match="heartbeat_interval must be > 0"):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=5.0,
                heartbeat_interval=0.0,
            )

    def test_raise_on_negative_election_timeout(self) -> None:
        """Test that negative election_timeout raises ValueError."""
        with pytest.raises(ValueError, match="election_timeout must be > 0"):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=-1.0,
                heartbeat_interval=1.0,
            )

    def test_raise_on_zero_election_timeout(self) -> None:
        """Test that zero election_timeout raises ValueError."""
        with pytest.raises(ValueError, match="election_timeout must be > 0"):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=0.0,
                heartbeat_interval=1.0,
            )

    def test_raise_when_timeout_equals_heartbeat(self) -> None:
        """Test that election_timeout = heartbeat_interval raises ValueError."""
        with pytest.raises(
            ValueError, match="election_timeout must be > heartbeat_interval"
        ):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=1.0,
                heartbeat_interval=1.0,
            )

    def test_raise_when_timeout_less_than_heartbeat(self) -> None:
        """Test that election_timeout < heartbeat_interval raises ValueError."""
        with pytest.raises(
            ValueError, match="election_timeout must be > heartbeat_interval"
        ):
            RaftLeaderElection(
                node_id="node-1",
                cluster_members=["node-1", "node-2"],
                election_timeout=0.5,
                heartbeat_interval=1.0,
            )

    def test_raise_when_node_id_not_in_cluster(self) -> None:
        """Test that node_id not in cluster_members raises ValueError."""
        with pytest.raises(ValueError, match="node_id .* not in cluster_members"):
            RaftLeaderElection(
                node_id="node-4",
                cluster_members=["node-1", "node-2", "node-3"],
                election_timeout=5.0,
                heartbeat_interval=1.0,
            )


@pytest.mark.unit
class TestLeaderElectionProtocol:
    """Test LeaderElectionPort protocol implementation."""

    def test_is_leader_elected_initially_false(self) -> None:
        """Test that is_leader_elected returns False initially."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.is_leader_elected() is False

    def test_elect_as_leader_sets_leader(self) -> None:
        """Test that elect_as_leader sets the node as leader."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        election.elect_as_leader()
        assert election.is_leader_elected() is True

    def test_demote_from_leader_removes_leadership(self) -> None:
        """Test that demote_from_leader removes leadership."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        election.elect_as_leader()
        assert election.is_leader_elected() is True
        election.demote_from_leader()
        assert election.is_leader_elected() is False

    def test_elect_as_leader_is_idempotent(self) -> None:
        """Test that elect_as_leader can be called multiple times (idempotent)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        election.elect_as_leader()
        election.elect_as_leader()
        election.elect_as_leader()
        assert election.is_leader_elected() is True

    def test_demote_from_leader_is_idempotent(self) -> None:
        """Test that demote_from_leader can be called multiple times (idempotent)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        election.demote_from_leader()
        election.demote_from_leader()
        election.demote_from_leader()
        assert election.is_leader_elected() is False


@pytest.mark.unit
class TestRaftClusterManagement:
    """Test Raft-specific cluster management methods."""

    def test_get_cluster_members_returns_list(self) -> None:
        """Test that get_cluster_members returns a list."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        members = election.get_cluster_members()
        assert isinstance(members, list)
        assert len(members) == 3

    def test_get_cluster_members_returns_copy(self) -> None:
        """Test that get_cluster_members returns a copy (mutations don't affect state)."""
        original_members = ["node-1", "node-2", "node-3"]
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=original_members,
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        members = election.get_cluster_members()
        members.append("node-4")
        # Original state should not be affected
        assert election.get_cluster_members() == ["node-1", "node-2", "node-3"]

    def test_get_cluster_members_with_empty_cluster(self) -> None:
        """Test that get_cluster_members returns empty list for uninitialized cluster."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        # Single node cluster
        members = election.get_cluster_members()
        assert members == ["node-1"]

    def test_is_member_in_cluster_with_existing_member(self) -> None:
        """Test is_member_in_cluster returns True for existing member."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.is_member_in_cluster("node-1") is True
        assert election.is_member_in_cluster("node-2") is True
        assert election.is_member_in_cluster("node-3") is True

    def test_is_member_in_cluster_with_nonexistent_member(self) -> None:
        """Test is_member_in_cluster returns False for non-existent member."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.is_member_in_cluster("node-3") is False
        assert election.is_member_in_cluster("node-99") is False
        assert election.is_member_in_cluster("") is False


@pytest.mark.unit
class TestRaftTimingConfiguration:
    """Test Raft timing configuration methods."""

    def test_get_election_timeout_returns_configured_value(self) -> None:
        """Test that get_election_timeout returns the configured value."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=7.5,
            heartbeat_interval=1.5,
        )
        assert election.get_election_timeout() == 7.5

    def test_get_election_timeout_returns_float(self) -> None:
        """Test that get_election_timeout returns a float."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        timeout = election.get_election_timeout()
        assert isinstance(timeout, float)
        assert timeout > 0

    def test_get_heartbeat_interval_returns_configured_value(self) -> None:
        """Test that get_heartbeat_interval returns the configured value."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=10.0,
            heartbeat_interval=2.5,
        )
        assert election.get_heartbeat_interval() == 2.5

    def test_get_heartbeat_interval_returns_float(self) -> None:
        """Test that get_heartbeat_interval returns a float."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        interval = election.get_heartbeat_interval()
        assert isinstance(interval, float)
        assert interval > 0

    def test_timing_invariant_heartbeat_less_than_timeout(self) -> None:
        """Test that heartbeat_interval is always < election_timeout."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.get_heartbeat_interval() < election.get_election_timeout()


@pytest.mark.unit
class TestRaftQuorumLogic:
    """Test Raft quorum consensus logic."""

    def test_is_quorum_reached_single_node_cluster(self) -> None:
        """Test quorum with single node (quorum = 1 node)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert election.is_quorum_reached() is True

    def test_is_quorum_reached_two_node_cluster(self) -> None:
        """Test quorum with two nodes (requires 2 nodes for quorum)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        # With 2 nodes, both must be present for quorum (> 1)
        assert election.is_quorum_reached() is True

    def test_is_quorum_reached_three_node_cluster(self) -> None:
        """Test quorum with three nodes (requires 2+ nodes for quorum)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        # With 3 nodes, all 3 are present so quorum is reached (> 1.5)
        assert election.is_quorum_reached() is True

    def test_is_quorum_reached_five_node_cluster(self) -> None:
        """Test quorum with five nodes (requires 3+ nodes for quorum)."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3", "node-4", "node-5"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        # With 5 nodes, need > 2.5 = 3+ nodes for quorum
        assert election.is_quorum_reached() is True

    def test_is_quorum_reached_returns_bool(self) -> None:
        """Test that is_quorum_reached returns a boolean."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        result = election.is_quorum_reached()
        assert isinstance(result, bool)


@pytest.mark.property
class TestQuorumInvariants:
    """Property-based tests for Raft quorum invariants."""

    @given(cluster_size=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_quorum_invariant_majority_logic(self, cluster_size: int) -> None:
        """Test quorum invariant: quorum requires > n/2 nodes.

        Property: For a cluster of size n, quorum is reached when > n/2 nodes
        are available. This is the fundamental property of Raft consensus.
        """
        cluster_members = [f"node-{i}" for i in range(cluster_size)]
        election = RaftLeaderElection(
            node_id="node-0",
            cluster_members=cluster_members,
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )

        # Calculate expected quorum
        quorum_threshold = (cluster_size // 2) + 1
        # All members are present in our in-memory implementation
        # So quorum is reached if cluster_size >= quorum_threshold
        expected_quorum = cluster_size >= quorum_threshold

        assert election.is_quorum_reached() is expected_quorum

    @given(
        cluster_size=st.integers(min_value=1, max_value=100),
        heartbeat_multiplier=st.floats(min_value=0.1, max_value=0.9),
    )
    @settings(max_examples=50)
    def test_timing_invariant_heartbeat_less_than_timeout(
        self, cluster_size: int, heartbeat_multiplier: float
    ) -> None:
        """Test timing invariant: heartbeat_interval < election_timeout.

        Property: For any valid Raft configuration, heartbeat interval must be
        strictly less than election timeout to prevent spurious elections.
        """
        cluster_members = [f"node-{i}" for i in range(cluster_size)]
        election_timeout = 10.0
        heartbeat_interval = election_timeout * heartbeat_multiplier

        election = RaftLeaderElection(
            node_id="node-0",
            cluster_members=cluster_members,
            election_timeout=election_timeout,
            heartbeat_interval=heartbeat_interval,
        )

        # Invariant: heartbeat must always be < timeout
        assert election.get_heartbeat_interval() < election.get_election_timeout()
        assert election.get_heartbeat_interval() == heartbeat_interval
        assert election.get_election_timeout() == election_timeout


@pytest.mark.unit
class TestProtocolCompliance:
    """Test that RaftLeaderElection satisfies the RaftLeaderElectionPort protocol."""

    def test_implements_leader_election_port(self) -> None:
        """Test that RaftLeaderElection has all LeaderElectionPort methods."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert hasattr(election, "is_leader_elected")
        assert hasattr(election, "elect_as_leader")
        assert hasattr(election, "demote_from_leader")
        assert callable(election.is_leader_elected)
        assert callable(election.elect_as_leader)
        assert callable(election.demote_from_leader)

    def test_implements_raft_leader_election_port(self) -> None:
        """Test that RaftLeaderElection has all RaftLeaderElectionPort methods."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2", "node-3"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )
        assert hasattr(election, "get_cluster_members")
        assert hasattr(election, "is_member_in_cluster")
        assert hasattr(election, "get_election_timeout")
        assert hasattr(election, "get_heartbeat_interval")
        assert hasattr(election, "is_quorum_reached")
        assert callable(election.get_cluster_members)
        assert callable(election.is_member_in_cluster)
        assert callable(election.get_election_timeout)
        assert callable(election.get_heartbeat_interval)
        assert callable(election.is_quorum_reached)

    def test_method_signatures_match_protocol(self) -> None:
        """Test that method signatures match the protocol specification."""
        election = RaftLeaderElection(
            node_id="node-1",
            cluster_members=["node-1", "node-2"],
            election_timeout=5.0,
            heartbeat_interval=1.0,
        )

        # is_leader_elected returns bool
        assert isinstance(election.is_leader_elected(), bool)

        # elect_as_leader returns None
        assert election.elect_as_leader() is None

        # demote_from_leader returns None
        assert election.demote_from_leader() is None

        # get_cluster_members returns list[str]
        members = election.get_cluster_members()
        assert isinstance(members, list)
        assert all(isinstance(m, str) for m in members)

        # is_member_in_cluster returns bool
        assert isinstance(election.is_member_in_cluster("node-1"), bool)

        # get_election_timeout returns float
        assert isinstance(election.get_election_timeout(), float)

        # get_heartbeat_interval returns float
        assert isinstance(election.get_heartbeat_interval(), float)

        # is_quorum_reached returns bool
        assert isinstance(election.is_quorum_reached(), bool)
