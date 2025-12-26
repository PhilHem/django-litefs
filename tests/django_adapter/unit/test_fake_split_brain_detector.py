"""Contract tests for FakeSplitBrainDetector.

These tests verify that FakeSplitBrainDetector implements SplitBrainDetectorPort
protocol correctly, ensuring test fakes behave as expected.
"""

import pytest

from litefs.adapters.ports import SplitBrainDetectorPort
from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.split_brain_detector import SplitBrainDetector

from .fakes import FakeSplitBrainDetector


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FakeSplitBrainDetector")
class TestFakeSplitBrainDetectorContract:
    """Verify FakeSplitBrainDetector implements SplitBrainDetectorPort."""

    def test_fake_implements_protocol(self) -> None:
        """Test FakeSplitBrainDetector satisfies SplitBrainDetectorPort protocol."""
        fake = FakeSplitBrainDetector()
        assert isinstance(fake, SplitBrainDetectorPort)

    def test_fake_default_healthy_cluster(self) -> None:
        """Test default state is a healthy cluster with single leader."""
        fake = FakeSplitBrainDetector()
        state = fake.get_cluster_state()

        assert state.has_single_leader() is True
        assert state.count_leaders() == 1

    def test_fake_configurable_via_constructor(self) -> None:
        """Test can configure cluster state via constructor."""
        split_brain_state = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
            ]
        )
        fake = FakeSplitBrainDetector(cluster_state=split_brain_state)

        state = fake.get_cluster_state()
        assert state.count_leaders() == 2
        assert state.has_single_leader() is False

    def test_fake_configurable_via_set_cluster_state(self) -> None:
        """Test can change cluster state via set_cluster_state()."""
        fake = FakeSplitBrainDetector()

        # Initial: healthy
        assert fake.get_cluster_state().has_single_leader() is True

        # Change to split-brain
        split_brain_state = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        fake.set_cluster_state(split_brain_state)

        assert fake.get_cluster_state().count_leaders() == 2

    def test_fake_error_injection(self) -> None:
        """Test can inject error to simulate failures."""
        fake = FakeSplitBrainDetector()

        fake.set_error(RuntimeError("Network unavailable"))
        with pytest.raises(RuntimeError, match="Network unavailable"):
            fake.get_cluster_state()

    def test_fake_clear_error(self) -> None:
        """Test can clear error after injection."""
        fake = FakeSplitBrainDetector()

        fake.set_error(RuntimeError("Test error"))
        with pytest.raises(RuntimeError):
            fake.get_cluster_state()

        # Clear error
        fake.set_error(None)
        state = fake.get_cluster_state()
        assert state.has_single_leader() is True

    def test_fake_works_with_split_brain_detector_use_case(self) -> None:
        """Test FakeSplitBrainDetector integrates with SplitBrainDetector use case."""
        # Configure split-brain scenario
        split_brain_state = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
            ]
        )
        fake = FakeSplitBrainDetector(cluster_state=split_brain_state)

        # Use with real SplitBrainDetector
        detector = SplitBrainDetector(port=fake)
        result = detector.detect_split_brain()

        assert result.is_split_brain is True
        assert len(result.leader_nodes) == 2

    def test_fake_no_leaders_scenario(self) -> None:
        """Test can configure cluster with no leaders."""
        no_leader_state = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=False),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        fake = FakeSplitBrainDetector(cluster_state=no_leader_state)

        state = fake.get_cluster_state()
        assert state.count_leaders() == 0
        assert state.has_single_leader() is False
