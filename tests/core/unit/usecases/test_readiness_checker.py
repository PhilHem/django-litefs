"""Unit tests for ReadinessChecker use case."""

import pytest

from litefs.usecases.readiness_checker import ReadinessChecker
from litefs.usecases.failover_coordinator import NodeState
from litefs.usecases.split_brain_detector import SplitBrainStatus
from litefs.domain.health import HealthStatus
from litefs.domain.split_brain import RaftNodeState


class FakeHealthChecker:
    """Fake HealthChecker for testing."""

    def __init__(self, state: str = "healthy") -> None:
        """Initialize with configurable health state."""
        self._state = state

    def check_health(self) -> HealthStatus:
        """Return configured health status."""
        return HealthStatus(state=self._state)  # type: ignore


class FakeFailoverCoordinator:
    """Fake FailoverCoordinator for testing."""

    def __init__(self, is_primary: bool = False) -> None:
        """Initialize with configurable primary state."""
        self._state = NodeState.PRIMARY if is_primary else NodeState.REPLICA

    @property
    def state(self) -> NodeState:
        """Return configured node state."""
        return self._state


class FakeSplitBrainDetector:
    """Fake SplitBrainDetector for testing."""

    def __init__(
        self,
        is_split_brain: bool = False,
        leader_nodes: list[RaftNodeState] | None = None,
    ) -> None:
        """Initialize with configurable split brain state."""
        self._is_split_brain = is_split_brain
        self._leader_nodes = leader_nodes or []

    def detect_split_brain(self) -> SplitBrainStatus:
        """Return configured split brain status."""
        return SplitBrainStatus(
            is_split_brain=self._is_split_brain,
            leader_nodes=self._leader_nodes,
        )


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ReadinessChecker")
class TestReadinessChecker:
    """Test ReadinessChecker use case."""

    def test_ready_when_healthy_and_no_split_brain(self) -> None:
        """Test node is ready when healthy and no split brain detected."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is True
        assert result.health_status.state == "healthy"
        assert result.split_brain_detected is False
        assert result.error is None

    def test_not_ready_when_unhealthy(self) -> None:
        """Test node is not ready when health status is unhealthy."""
        health_checker = FakeHealthChecker(state="unhealthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is False
        assert result.health_status.state == "unhealthy"
        assert result.error is not None
        assert "unhealthy" in result.error.lower()

    def test_not_ready_when_degraded(self) -> None:
        """Test node is not ready when health status is degraded."""
        health_checker = FakeHealthChecker(state="degraded")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is False
        assert result.health_status.state == "degraded"
        assert result.error is not None
        assert "degraded" in result.error.lower()

    def test_can_accept_writes_when_primary(self) -> None:
        """Test can_accept_writes is True when node is PRIMARY."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.can_accept_writes is True

    def test_cannot_accept_writes_when_replica(self) -> None:
        """Test can_accept_writes is False when node is REPLICA."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=False)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.can_accept_writes is False

    def test_not_ready_when_split_brain_detected(self) -> None:
        """Test node is not ready when split brain is detected."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)
        leader_nodes = [
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=True),
        ]
        split_brain_detector = FakeSplitBrainDetector(
            is_split_brain=True,
            leader_nodes=leader_nodes,
        )

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
            split_brain_detector=split_brain_detector,
        )
        result = checker.check_readiness()

        assert result.is_ready is False
        assert result.split_brain_detected is True
        assert result.error is not None
        assert "split" in result.error.lower() and "brain" in result.error.lower()

    def test_ready_without_split_brain_detector(self) -> None:
        """Test node is ready when split_brain_detector is not provided."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
            split_brain_detector=None,
        )
        result = checker.check_readiness()

        assert result.is_ready is True
        assert result.split_brain_detected is False
        assert result.leader_node_ids == ()

    def test_leader_node_ids_from_split_brain(self) -> None:
        """Test leader_node_ids is populated from split brain detection."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)
        leader_nodes = [
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=True),
        ]
        split_brain_detector = FakeSplitBrainDetector(
            is_split_brain=True,
            leader_nodes=leader_nodes,
        )

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
            split_brain_detector=split_brain_detector,
        )
        result = checker.check_readiness()

        assert result.leader_node_ids == ("node-1", "node-2")

    def test_error_message_when_unhealthy(self) -> None:
        """Test error message is set when node is unhealthy."""
        health_checker = FakeHealthChecker(state="unhealthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.error is not None
        assert "unhealthy" in result.error.lower()

    def test_error_message_when_split_brain(self) -> None:
        """Test error message is set when split brain detected."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)
        leader_nodes = [
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=True),
        ]
        split_brain_detector = FakeSplitBrainDetector(
            is_split_brain=True,
            leader_nodes=leader_nodes,
        )

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
            split_brain_detector=split_brain_detector,
        )
        result = checker.check_readiness()

        assert result.error is not None
        assert "split" in result.error.lower()

    def test_healthy_replica_is_ready(self) -> None:
        """Test that a healthy replica node is ready to serve reads."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=False)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is True
        assert result.can_accept_writes is False
        assert result.error is None

    def test_no_split_brain_with_single_leader(self) -> None:
        """Test no split brain when only one leader exists."""
        health_checker = FakeHealthChecker(state="healthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)
        leader_nodes = [
            RaftNodeState(node_id="node-1", is_leader=True),
        ]
        split_brain_detector = FakeSplitBrainDetector(
            is_split_brain=False,
            leader_nodes=leader_nodes,
        )

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
            split_brain_detector=split_brain_detector,
        )
        result = checker.check_readiness()

        assert result.is_ready is True
        assert result.split_brain_detected is False
        assert result.leader_node_ids == ("node-1",)

    def test_degraded_primary_is_not_ready(self) -> None:
        """Test degraded PRIMARY node is not ready (cannot accept writes)."""
        health_checker = FakeHealthChecker(state="degraded")
        failover_coordinator = FakeFailoverCoordinator(is_primary=True)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is False
        assert result.can_accept_writes is False
        assert result.error is not None
        assert "degraded" in result.error.lower()

    def test_degraded_replica_is_ready(self) -> None:
        """Test degraded REPLICA node is still ready (can serve reads)."""
        health_checker = FakeHealthChecker(state="degraded")
        failover_coordinator = FakeFailoverCoordinator(is_primary=False)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is True
        assert result.can_accept_writes is False
        assert result.error is None

    def test_unhealthy_replica_is_not_ready(self) -> None:
        """Test unhealthy REPLICA node is not ready (cannot serve anything)."""
        health_checker = FakeHealthChecker(state="unhealthy")
        failover_coordinator = FakeFailoverCoordinator(is_primary=False)

        checker = ReadinessChecker(
            health_checker=health_checker,
            failover_coordinator=failover_coordinator,
        )
        result = checker.check_readiness()

        assert result.is_ready is False
        assert result.can_accept_writes is False
        assert result.error is not None
        assert "unhealthy" in result.error.lower()
