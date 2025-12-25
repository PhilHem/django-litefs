"""Unit tests for SplitBrainDetector use case."""

import pytest
from hypothesis import given, strategies as st

from litefs.usecases.split_brain_detector import SplitBrainDetector, SplitBrainStatus
from litefs.domain.split_brain import RaftNodeState, RaftClusterState
from litefs.adapters.ports import SplitBrainDetectorPort


class MockSplitBrainDetectorPort:
    """Mock implementation of SplitBrainDetectorPort for testing."""

    def __init__(self, cluster_state: RaftClusterState | None = None) -> None:
        """Initialize mock with cluster state."""
        if cluster_state is None:
            # Default: single node cluster with one leader
            cluster_state = RaftClusterState(
                nodes=[RaftNodeState(node_id="node1", is_leader=True)]
            )
        self.cluster_state = cluster_state

    def get_cluster_state(self) -> RaftClusterState:
        """Return the cluster state."""
        return self.cluster_state


@pytest.mark.unit
class TestSplitBrainDetector:
    """Test SplitBrainDetector use case."""

    def test_initialize_with_port(self) -> None:
        """Test initializing SplitBrainDetector with a port."""
        port = MockSplitBrainDetectorPort()
        detector = SplitBrainDetector(port=port)

        assert detector.port == port

    def test_detect_no_split_brain_single_leader(self) -> None:
        """Test detection when cluster has single leader."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 1
        assert status.leader_nodes[0].node_id == "node1"

    def test_detect_split_brain_two_leaders(self) -> None:
        """Test detection when cluster has two leaders (split-brain)."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is True
        assert len(status.leader_nodes) == 2
        assert {n.node_id for n in status.leader_nodes} == {"node1", "node2"}

    def test_detect_split_brain_three_leaders(self) -> None:
        """Test detection when cluster has three leaders."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
                RaftNodeState(node_id="node3", is_leader=True),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is True
        assert len(status.leader_nodes) == 3

    def test_detect_no_leaders(self) -> None:
        """Test detection when cluster has no leaders."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=False),
                RaftNodeState(node_id="node2", is_leader=False),
                RaftNodeState(node_id="node3", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 0

    def test_detect_single_node_cluster_with_leader(self) -> None:
        """Test detection in single-node cluster."""
        cluster = RaftClusterState(
            nodes=[RaftNodeState(node_id="node1", is_leader=True)]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 1

    def test_split_brain_status_contains_leader_details(self) -> None:
        """Test that SplitBrainStatus contains correct leader information."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="primary1", is_leader=True),
                RaftNodeState(node_id="primary2", is_leader=True),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        assert status.is_split_brain is True
        leader_ids = {n.node_id for n in status.leader_nodes}
        assert leader_ids == {"primary1", "primary2"}

    def test_multiple_consecutive_detections(self) -> None:
        """Test that multiple detections work correctly."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        # First detection
        status1 = detector.detect_split_brain()
        assert status1.is_split_brain is False

        # Second detection (should be consistent)
        status2 = detector.detect_split_brain()
        assert status2.is_split_brain is False
        assert status1.is_split_brain == status2.is_split_brain

    def test_detection_after_cluster_change(self) -> None:
        """Test detection after cluster state changes."""
        # Start with single leader
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status1 = detector.detect_split_brain()
        assert status1.is_split_brain is False

        # Simulate cluster state change: node2 becomes leader
        cluster_with_split = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=True),
            ]
        )
        port.cluster_state = cluster_with_split

        status2 = detector.detect_split_brain()
        assert status2.is_split_brain is True

    def test_uses_split_brain_detector_port_abstraction(self) -> None:
        """Test that detector uses SplitBrainDetectorPort abstraction."""
        port = MockSplitBrainDetectorPort()
        detector = SplitBrainDetector(port=port)

        # Detector should rely on port interface
        assert isinstance(port, SplitBrainDetectorPort) or hasattr(
            port, "get_cluster_state"
        )
        detector.detect_split_brain()
        # Should execute without errors


@pytest.mark.unit
class TestSplitBrainStatus:
    """Test SplitBrainStatus value object."""

    def test_create_no_split_brain(self) -> None:
        """Test creating status for normal cluster."""
        leader = RaftNodeState(node_id="node1", is_leader=True)
        status = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])

        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 1

    def test_create_with_split_brain(self) -> None:
        """Test creating status for split-brain cluster."""
        leaders = [
            RaftNodeState(node_id="node1", is_leader=True),
            RaftNodeState(node_id="node2", is_leader=True),
        ]
        status = SplitBrainStatus(is_split_brain=True, leader_nodes=leaders)

        assert status.is_split_brain is True
        assert len(status.leader_nodes) == 2

    def test_create_with_no_leaders(self) -> None:
        """Test creating status when no leaders exist."""
        status = SplitBrainStatus(is_split_brain=False, leader_nodes=[])

        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 0

    def test_frozen_dataclass(self) -> None:
        """Test that SplitBrainStatus is immutable."""
        leader = RaftNodeState(node_id="node1", is_leader=True)
        status = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])

        with pytest.raises(AttributeError):
            status.is_split_brain = True  # type: ignore

    def test_equality(self) -> None:
        """Test equality comparison for SplitBrainStatus."""
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        status1 = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader1])

        leader2 = RaftNodeState(node_id="node1", is_leader=True)
        status2 = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader2])

        assert status1 == status2

    def test_inequality_different_split_brain_flag(self) -> None:
        """Test inequality when split-brain flag differs."""
        leader = RaftNodeState(node_id="node1", is_leader=True)
        status1 = SplitBrainStatus(is_split_brain=True, leader_nodes=[leader])
        status2 = SplitBrainStatus(is_split_brain=False, leader_nodes=[leader])

        assert status1 != status2

    def test_inequality_different_leaders(self) -> None:
        """Test inequality when leader lists differ."""
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        leader2 = RaftNodeState(node_id="node2", is_leader=True)

        status1 = SplitBrainStatus(is_split_brain=True, leader_nodes=[leader1])
        status2 = SplitBrainStatus(is_split_brain=True, leader_nodes=[leader2])

        assert status1 != status2


@pytest.mark.unit
@pytest.mark.property
class TestSplitBrainDetectorPBT:
    """Property-based tests for SplitBrainDetector."""

    @given(
        leader_count=st.integers(min_value=0, max_value=5),
        replica_count=st.integers(min_value=1, max_value=5),
    )
    def test_detection_matches_leader_count(
        self, leader_count: int, replica_count: int
    ) -> None:
        """PBT: Split-brain detection should match leader count.

        Split-brain is detected when 2+ leaders exist. Single leader (1)
        or no leaders (0) are not split-brain.
        """
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
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        # Split-brain is true when leader_count >= 2
        assert status.is_split_brain == (leader_count >= 2)
        # Leader list should have exactly leader_count items
        assert len(status.leader_nodes) == leader_count

    @given(
        leader_count=st.integers(min_value=2, max_value=5),
        replica_count=st.integers(min_value=1, max_value=5),
    )
    def test_split_brain_multiple_leaders(
        self, leader_count: int, replica_count: int
    ) -> None:
        """PBT: Multiple leaders should always result in split-brain detection."""
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
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        # With multiple leaders, split-brain must be detected
        assert status.is_split_brain is True
        assert len(status.leader_nodes) == leader_count

    @given(
        replica_count=st.integers(min_value=0, max_value=5),
    )
    def test_single_leader_no_split_brain(self, replica_count: int) -> None:
        """PBT: Single leader should never trigger split-brain detection."""
        nodes = [RaftNodeState(node_id="leader", is_leader=True)]
        nodes.extend(
            [
                RaftNodeState(node_id=f"replica{i}", is_leader=False)
                for i in range(replica_count)
            ]
        )

        cluster = RaftClusterState(nodes=nodes)
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        # With single leader, split-brain must be false
        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 1

    @given(
        replica_count=st.integers(min_value=1, max_value=5),
    )
    def test_no_leaders_no_split_brain_flag(self, replica_count: int) -> None:
        """PBT: No leaders should result in is_split_brain=False."""
        replicas = [
            RaftNodeState(node_id=f"replica{i}", is_leader=False)
            for i in range(replica_count)
        ]

        cluster = RaftClusterState(nodes=replicas)
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        status = detector.detect_split_brain()

        # No leaders means no split-brain
        assert status.is_split_brain is False
        assert len(status.leader_nodes) == 0

    def test_idempotent_detection(self) -> None:
        """PBT: Multiple detections should be idempotent."""
        cluster = RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node1", is_leader=True),
                RaftNodeState(node_id="node2", is_leader=False),
            ]
        )
        port = MockSplitBrainDetectorPort(cluster_state=cluster)
        detector = SplitBrainDetector(port=port)

        # Call detect_split_brain multiple times
        results = [detector.detect_split_brain() for _ in range(10)]

        # All results should be identical
        assert all(r.is_split_brain == results[0].is_split_brain for r in results)
