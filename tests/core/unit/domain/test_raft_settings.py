"""Unit tests for RaftSettings and QuorumPolicy domain value objects."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.raft import RaftSettings, QuorumPolicy
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestRaftSettings:
    """Test RaftSettings value object."""

    def test_create_with_valid_settings(self):
        """Test creating RaftSettings with valid configuration."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        assert settings.node_id == "node1"
        assert settings.cluster_members == ("node1", "node2", "node3")
        assert settings.quorum_size == 2  # floor(3/2) + 1 = 2

    def test_quorum_size_calculation_three_nodes(self):
        """Test quorum size calculation for 3-node cluster."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        # floor(3/2) + 1 = floor(1.5) + 1 = 1 + 1 = 2
        assert settings.quorum_size == 2

    def test_quorum_size_calculation_five_nodes(self):
        """Test quorum size calculation for 5-node cluster."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3", "node4", "node5"],
        )
        # floor(5/2) + 1 = floor(2.5) + 1 = 2 + 1 = 3
        assert settings.quorum_size == 3

    def test_quorum_size_calculation_two_nodes(self):
        """Test quorum size calculation for 2-node cluster."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        # floor(2/2) + 1 = floor(1) + 1 = 1 + 1 = 2
        assert settings.quorum_size == 2

    def test_quorum_size_calculation_one_node(self):
        """Test quorum size calculation for single-node cluster."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1"],
        )
        # floor(1/2) + 1 = floor(0.5) + 1 = 0 + 1 = 1
        assert settings.quorum_size == 1

    def test_frozen_dataclass(self):
        """Test that RaftSettings is immutable."""
        settings = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        with pytest.raises(AttributeError):
            settings.node_id = "node2"  # type: ignore

    def test_reject_node_id_not_in_cluster(self):
        """Test that node_id must be in cluster_members."""
        with pytest.raises(
            LiteFSConfigError, match="must be a member of cluster_members"
        ):
            RaftSettings(
                node_id="node4",
                cluster_members=["node1", "node2", "node3"],
            )

    def test_reject_empty_node_id(self):
        """Test that empty node_id is rejected."""
        with pytest.raises(LiteFSConfigError, match="node_id cannot be empty"):
            RaftSettings(
                node_id="",
                cluster_members=["node1"],
            )

    def test_reject_whitespace_only_node_id(self):
        """Test that whitespace-only node_id is rejected."""
        with pytest.raises(
            LiteFSConfigError, match="node_id cannot be whitespace-only"
        ):
            RaftSettings(
                node_id="   ",
                cluster_members=["node1", "   "],
            )

    def test_reject_empty_cluster_members(self):
        """Test that empty cluster_members list is rejected."""
        with pytest.raises(LiteFSConfigError, match="cluster_members cannot be empty"):
            RaftSettings(
                node_id="node1",
                cluster_members=[],
            )

    def test_reject_empty_string_in_cluster_members(self):
        """Test that empty strings in cluster_members are rejected."""
        with pytest.raises(LiteFSConfigError, match="cluster_members contains empty"):
            RaftSettings(
                node_id="node1",
                cluster_members=["node1", "", "node3"],
            )

    def test_reject_whitespace_only_in_cluster_members(self):
        """Test that whitespace-only strings in cluster_members are rejected."""
        with pytest.raises(
            LiteFSConfigError, match="cluster_members contains whitespace-only"
        ):
            RaftSettings(
                node_id="node1",
                cluster_members=["node1", "   ", "node3"],
            )

    def test_equality(self):
        """Test that configs with same values are equal."""
        settings1 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        settings2 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        assert settings1 == settings2

    def test_inequality_different_node_id(self):
        """Test that configs with different node_id are not equal."""
        settings1 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        settings2 = RaftSettings(
            node_id="node2",
            cluster_members=["node1", "node2"],
        )
        assert settings1 != settings2

    def test_inequality_different_cluster_members(self):
        """Test that configs with different cluster_members are not equal."""
        settings1 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        settings2 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        assert settings1 != settings2

    def test_hash_consistency(self):
        """Test that configs with same values have same hash."""
        settings1 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        settings2 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2", "node3"],
        )
        assert hash(settings1) == hash(settings2)

    def test_can_use_in_set(self):
        """Test that RaftSettings can be used in sets."""
        settings1 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        settings2 = RaftSettings(
            node_id="node1",
            cluster_members=["node1", "node2"],
        )
        settings3 = RaftSettings(
            node_id="node2",
            cluster_members=["node1", "node2"],
        )

        settings_set = {settings1, settings2, settings3}
        assert len(settings_set) == 2  # settings1 and settings2 are equal


@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
class TestRaftSettingsPBT:
    """Property-based tests for RaftSettings."""

    @given(
        cluster_size=st.integers(min_value=1, max_value=100),
    )
    def test_quorum_size_property_greater_than_half(self, cluster_size):
        """PBT: Quorum size must always be > n/2."""
        cluster_members = [f"node{i}" for i in range(cluster_size)]

        settings = RaftSettings(
            node_id=cluster_members[0],
            cluster_members=cluster_members,
        )

        # Quorum must be > n/2
        assert settings.quorum_size > cluster_size / 2

    @given(
        cluster_size=st.integers(min_value=1, max_value=100),
    )
    def test_quorum_size_property_formula(self, cluster_size):
        """PBT: Quorum size must equal floor(n/2) + 1."""
        cluster_members = [f"node{i}" for i in range(cluster_size)]

        settings = RaftSettings(
            node_id=cluster_members[0],
            cluster_members=cluster_members,
        )

        expected_quorum = cluster_size // 2 + 1
        assert settings.quorum_size == expected_quorum

    @given(
        node_id=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=50,
        ),
    )
    def test_valid_node_ids_accepted(self, node_id):
        """PBT: Valid node IDs should be accepted."""
        settings = RaftSettings(
            node_id=node_id,
            cluster_members=[node_id, "node2"],
        )
        assert settings.node_id == node_id

    @given(
        cluster_members=st.lists(
            st.text(
                alphabet=st.characters(
                    min_codepoint=33,
                    max_codepoint=126,
                    blacklist_characters=" \t\n\r",
                ),
                min_size=1,
                max_size=20,
            ),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    def test_idempotent_creation(self, cluster_members):
        """PBT: Creating settings with same values should be idempotent."""
        node_id = cluster_members[0]

        settings1 = RaftSettings(
            node_id=node_id,
            cluster_members=cluster_members,
        )
        settings2 = RaftSettings(
            node_id=node_id,
            cluster_members=cluster_members,
        )

        assert settings1 == settings2
        assert hash(settings1) == hash(settings2)


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestQuorumPolicy:
    """Test QuorumPolicy value object."""

    def test_create_with_valid_settings(self):
        """Test creating QuorumPolicy with valid configuration."""
        policy = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        assert policy.election_timeout_ms == 500
        assert policy.heartbeat_interval_ms == 100

    def test_frozen_dataclass(self):
        """Test that QuorumPolicy is immutable."""
        policy = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        with pytest.raises(AttributeError):
            policy.election_timeout_ms = 600  # type: ignore

    def test_reject_election_timeout_less_than_heartbeat(self):
        """Test that election_timeout must be > heartbeat_interval."""
        with pytest.raises(
            LiteFSConfigError,
            match="heartbeat_interval_ms must be less than election_timeout_ms",
        ):
            QuorumPolicy(
                election_timeout_ms=100,
                heartbeat_interval_ms=100,
            )

    def test_reject_election_timeout_less_than_heartbeat_by_one(self):
        """Test that election_timeout must be strictly greater than heartbeat."""
        with pytest.raises(LiteFSConfigError):
            QuorumPolicy(
                election_timeout_ms=100,
                heartbeat_interval_ms=101,
            )

    def test_reject_negative_election_timeout(self):
        """Test that negative election_timeout is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be positive"):
            QuorumPolicy(
                election_timeout_ms=-100,
                heartbeat_interval_ms=50,
            )

    def test_reject_zero_election_timeout(self):
        """Test that zero election_timeout is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be positive"):
            QuorumPolicy(
                election_timeout_ms=0,
                heartbeat_interval_ms=50,
            )

    def test_reject_negative_heartbeat_interval(self):
        """Test that negative heartbeat_interval is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be positive"):
            QuorumPolicy(
                election_timeout_ms=500,
                heartbeat_interval_ms=-100,
            )

    def test_reject_zero_heartbeat_interval(self):
        """Test that zero heartbeat_interval is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be positive"):
            QuorumPolicy(
                election_timeout_ms=500,
                heartbeat_interval_ms=0,
            )

    def test_equality(self):
        """Test that policies with same values are equal."""
        policy1 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy2 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        assert policy1 == policy2

    def test_inequality_different_election_timeout(self):
        """Test that policies with different election_timeout are not equal."""
        policy1 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy2 = QuorumPolicy(
            election_timeout_ms=600,
            heartbeat_interval_ms=100,
        )
        assert policy1 != policy2

    def test_inequality_different_heartbeat_interval(self):
        """Test that policies with different heartbeat_interval are not equal."""
        policy1 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy2 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=150,
        )
        assert policy1 != policy2

    def test_hash_consistency(self):
        """Test that policies with same values have same hash."""
        policy1 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy2 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        assert hash(policy1) == hash(policy2)

    def test_can_use_in_set(self):
        """Test that QuorumPolicy can be used in sets."""
        policy1 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy2 = QuorumPolicy(
            election_timeout_ms=500,
            heartbeat_interval_ms=100,
        )
        policy3 = QuorumPolicy(
            election_timeout_ms=600,
            heartbeat_interval_ms=100,
        )

        policy_set = {policy1, policy2, policy3}
        assert len(policy_set) == 2  # policy1 and policy2 are equal

    def test_typical_raft_timeouts(self):
        """Test typical Raft timeout values."""
        # Typical Raft uses 300-500ms election timeout, 50-150ms heartbeat
        policy = QuorumPolicy(
            election_timeout_ms=400,
            heartbeat_interval_ms=100,
        )
        assert policy.election_timeout_ms == 400
        assert policy.heartbeat_interval_ms == 100


@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
class TestQuorumPolicyPBT:
    """Property-based tests for QuorumPolicy."""

    @given(
        election_timeout=st.integers(min_value=101, max_value=10000),
        heartbeat_interval=st.integers(min_value=1, max_value=100),
    )
    def test_valid_intervals_accepted(self, election_timeout, heartbeat_interval):
        """PBT: Valid timeout/interval pairs should be accepted."""
        if heartbeat_interval < election_timeout:
            policy = QuorumPolicy(
                election_timeout_ms=election_timeout,
                heartbeat_interval_ms=heartbeat_interval,
            )
            assert policy.election_timeout_ms == election_timeout
            assert policy.heartbeat_interval_ms == heartbeat_interval

    @given(
        election_timeout=st.integers(min_value=1, max_value=10000),
        heartbeat_interval=st.integers(min_value=1, max_value=10000),
    )
    def test_heartbeat_must_be_less_than_election_timeout(
        self, election_timeout, heartbeat_interval
    ):
        """PBT: heartbeat_interval must always be < election_timeout."""
        if heartbeat_interval >= election_timeout:
            with pytest.raises(LiteFSConfigError):
                QuorumPolicy(
                    election_timeout_ms=election_timeout,
                    heartbeat_interval_ms=heartbeat_interval,
                )

    @given(
        election_timeout=st.integers(min_value=1, max_value=10000),
        heartbeat_interval=st.integers(min_value=1, max_value=10000),
    )
    def test_positive_integers_required(self, election_timeout, heartbeat_interval):
        """PBT: Both intervals must be positive integers."""
        # Only test valid cases where both are positive
        if election_timeout > 0 and heartbeat_interval > 0:
            if heartbeat_interval < election_timeout:
                policy = QuorumPolicy(
                    election_timeout_ms=election_timeout,
                    heartbeat_interval_ms=heartbeat_interval,
                )
                assert policy.election_timeout_ms > 0
                assert policy.heartbeat_interval_ms > 0

    @given(
        election_timeout=st.integers(min_value=2, max_value=10000),
        heartbeat_interval=st.integers(min_value=1, max_value=10000),
    )
    def test_idempotent_creation(self, election_timeout, heartbeat_interval):
        """PBT: Creating policy with same values should be idempotent."""
        if heartbeat_interval < election_timeout:
            policy1 = QuorumPolicy(
                election_timeout_ms=election_timeout,
                heartbeat_interval_ms=heartbeat_interval,
            )
            policy2 = QuorumPolicy(
                election_timeout_ms=election_timeout,
                heartbeat_interval_ms=heartbeat_interval,
            )

            assert policy1 == policy2
            assert hash(policy1) == hash(policy2)
