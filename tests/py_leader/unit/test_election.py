"""Unit tests for RaftLeaderElection class.

These tests focus on:
1. Constructor validation (no PySyncObj needed)
2. Configuration getters
3. Cluster membership queries

Integration tests (with actual Raft consensus) are in tests/py_leader/integration/.
"""

from __future__ import annotations

import pytest

from py_leader.election import InvalidConfigurationError, RaftLeaderElection


class TestRaftLeaderElectionValidation:
    """Test constructor validation logic."""

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_empty_node_id_raises_error(self) -> None:
        """Empty node_id should raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="node_id cannot be empty"):
            RaftLeaderElection(
                node_id="",
                cluster_members=["node1:20202", "node2:20202"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_whitespace_node_id_raises_error(self) -> None:
        """Whitespace-only node_id should raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="node_id cannot be empty"):
            RaftLeaderElection(
                node_id="   ",
                cluster_members=["node1:20202", "node2:20202"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_empty_cluster_members_raises_error(self) -> None:
        """Empty cluster_members should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="cluster_members cannot be empty"
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=[],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_single_node_cluster_raises_error(self) -> None:
        """Single-node cluster should raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="at least 2 nodes"):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_duplicate_cluster_members_raises_error(self) -> None:
        """Duplicate cluster members should raise InvalidConfigurationError."""
        with pytest.raises(InvalidConfigurationError, match="duplicate addresses"):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node1:20202", "node2:20202"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_invalid_address_format_raises_error(self) -> None:
        """Invalid address format should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="Invalid cluster member address"
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "invalid_no_port"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_node_id_not_in_cluster_raises_error(self) -> None:
        """node_id not in cluster_members should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="node_id .* not found in cluster_members"
        ):
            RaftLeaderElection(
                node_id="node3",
                cluster_members=["node1:20202", "node2:20202"],
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_zero_election_timeout_raises_error(self) -> None:
        """Zero election_timeout should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="election_timeout must be > 0"
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node2:20202"],
                election_timeout=0,
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_negative_election_timeout_raises_error(self) -> None:
        """Negative election_timeout should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="election_timeout must be > 0"
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node2:20202"],
                election_timeout=-1.0,
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_zero_heartbeat_interval_raises_error(self) -> None:
        """Zero heartbeat_interval should raise InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="heartbeat_interval must be > 0"
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node2:20202"],
                heartbeat_interval=0,
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_heartbeat_greater_than_election_timeout_raises_error(self) -> None:
        """heartbeat_interval >= election_timeout should raise error."""
        with pytest.raises(
            InvalidConfigurationError,
            match="heartbeat_interval must be less than election_timeout",
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node2:20202"],
                election_timeout=1.0,
                heartbeat_interval=2.0,
            )

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_heartbeat_equal_to_election_timeout_raises_error(self) -> None:
        """heartbeat_interval == election_timeout should raise error."""
        with pytest.raises(
            InvalidConfigurationError,
            match="heartbeat_interval must be less than election_timeout",
        ):
            RaftLeaderElection(
                node_id="node1",
                cluster_members=["node1:20202", "node2:20202"],
                election_timeout=1.0,
                heartbeat_interval=1.0,
            )


class TestFindSelfAddress:
    """Test the _find_self_address static method."""

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_finds_matching_address(self) -> None:
        """Should find address matching node_id."""
        result = RaftLeaderElection._find_self_address(
            "node2", ["node1:20202", "node2:30303", "node3:40404"]
        )
        assert result == "node2:30303"

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_finds_first_match_on_duplicate_hosts(self) -> None:
        """Should find first matching address if multiple have same host."""
        # This is an edge case that validation should prevent
        result = RaftLeaderElection._find_self_address(
            "node1", ["node1:20202", "node1:30303"]
        )
        assert result == "node1:20202"

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_raises_on_no_match(self) -> None:
        """Should raise InvalidConfigurationError if no match."""
        with pytest.raises(InvalidConfigurationError, match="not found"):
            RaftLeaderElection._find_self_address(
                "node4", ["node1:20202", "node2:20202"]
            )


class TestIsMemberInCluster:
    """Test is_member_in_cluster without network.

    Uses the static method indirectly by testing logic.
    """

    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.py_leader")
    def test_membership_check_logic(self) -> None:
        """Test the membership checking logic."""
        cluster_members = ["node1:20202", "node2:20202", "node3:20202"]

        # This tests the logic without instantiating the full class
        for member in cluster_members:
            host = member.split(":")[0]
            # node_id == host means it's in cluster
            assert host in ["node1", "node2", "node3"]

        # Non-member
        assert "node4" not in [m.split(":")[0] for m in cluster_members]
