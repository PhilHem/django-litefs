"""Tests for fake adapters used in unit testing."""

from __future__ import annotations

import pytest

from litefs.domain.health import HealthStatus
from litefs.usecases.failover_coordinator import NodeState
from litefs.usecases.primary_detector import LiteFSNotRunningError

from .fakes import FakeFailoverCoordinator, FakeHealthChecker, FakePrimaryDetector


@pytest.mark.unit
class TestFakeHealthChecker:
    """Tests for FakeHealthChecker."""

    def test_default_healthy(self) -> None:
        """FakeHealthChecker defaults to healthy state."""
        checker = FakeHealthChecker()
        status = checker.check_health()
        assert status.state == "healthy"

    def test_set_health_status_degraded(self) -> None:
        """set_health_status changes returned health state."""
        checker = FakeHealthChecker()
        checker.set_health_status("degraded")
        status = checker.check_health()
        assert status.state == "degraded"

    def test_set_health_status_unhealthy(self) -> None:
        """set_health_status changes returned health state."""
        checker = FakeHealthChecker()
        checker.set_health_status("unhealthy")
        status = checker.check_health()
        assert status.state == "unhealthy"

    def test_check_health_returns_health_status(self) -> None:
        """check_health returns a HealthStatus value object."""
        checker = FakeHealthChecker()
        status = checker.check_health()
        assert isinstance(status, HealthStatus)


@pytest.mark.unit
class TestFakeFailoverCoordinator:
    """Tests for FakeFailoverCoordinator."""

    def test_default_primary(self) -> None:
        """FakeFailoverCoordinator defaults to PRIMARY state."""
        coordinator = FakeFailoverCoordinator()
        assert coordinator.state == NodeState.PRIMARY

    def test_set_node_state_replica(self) -> None:
        """set_node_state changes returned node state."""
        coordinator = FakeFailoverCoordinator()
        coordinator.set_node_state(NodeState.REPLICA)
        assert coordinator.state == NodeState.REPLICA

    def test_coordinate_transition_noop(self) -> None:
        """coordinate_transition is a no-op in the fake."""
        coordinator = FakeFailoverCoordinator()
        coordinator.set_node_state(NodeState.REPLICA)
        coordinator.coordinate_transition()
        # State unchanged - fake doesn't actually coordinate
        assert coordinator.state == NodeState.REPLICA

    def test_can_become_leader_default_true(self) -> None:
        """can_become_leader returns True by default."""
        coordinator = FakeFailoverCoordinator()
        assert coordinator.can_become_leader() is True

    def test_is_healthy_default_true(self) -> None:
        """is_healthy returns True by default."""
        coordinator = FakeFailoverCoordinator()
        assert coordinator.is_healthy() is True

    def test_mark_unhealthy(self) -> None:
        """mark_unhealthy sets healthy flag to False."""
        coordinator = FakeFailoverCoordinator()
        coordinator.mark_unhealthy()
        assert coordinator.is_healthy() is False

    def test_mark_healthy(self) -> None:
        """mark_healthy sets healthy flag to True."""
        coordinator = FakeFailoverCoordinator()
        coordinator.mark_unhealthy()
        coordinator.mark_healthy()
        assert coordinator.is_healthy() is True

    def test_can_maintain_leadership(self) -> None:
        """can_maintain_leadership returns configurable value."""
        coordinator = FakeFailoverCoordinator()
        assert coordinator.can_maintain_leadership() is True
        coordinator.set_can_maintain_leadership(False)
        assert coordinator.can_maintain_leadership() is False

    def test_perform_graceful_handoff(self) -> None:
        """perform_graceful_handoff transitions to REPLICA."""
        coordinator = FakeFailoverCoordinator()
        coordinator.perform_graceful_handoff()
        assert coordinator.state == NodeState.REPLICA

    def test_demote_for_health(self) -> None:
        """demote_for_health transitions to REPLICA."""
        coordinator = FakeFailoverCoordinator()
        coordinator.demote_for_health()
        assert coordinator.state == NodeState.REPLICA

    def test_demote_for_quorum_loss(self) -> None:
        """demote_for_quorum_loss transitions to REPLICA."""
        coordinator = FakeFailoverCoordinator()
        coordinator.demote_for_quorum_loss()
        assert coordinator.state == NodeState.REPLICA


@pytest.mark.unit
class TestFakePrimaryDetector:
    """Tests for FakePrimaryDetector LiteFS-not-running simulation."""

    def test_set_litefs_not_running_causes_is_primary_to_raise(self) -> None:
        """set_litefs_not_running causes is_primary to raise LiteFSNotRunningError."""
        detector = FakePrimaryDetector()
        detector.set_litefs_not_running()
        with pytest.raises(LiteFSNotRunningError):
            detector.is_primary()

    def test_default_behavior_unchanged(self) -> None:
        """Default behavior (LiteFS running) still works after adding method."""
        detector = FakePrimaryDetector()
        # Default is primary
        assert detector.is_primary() is True

        # Can still toggle primary state
        detector.set_primary(False)
        assert detector.is_primary() is False

    def test_set_litefs_not_running_clears_primary_state(self) -> None:
        """After set_litefs_not_running, is_primary raises even if was primary."""
        detector = FakePrimaryDetector(is_primary=True)
        detector.set_litefs_not_running()
        with pytest.raises(LiteFSNotRunningError):
            detector.is_primary()

    def test_error_message_contains_context(self) -> None:
        """LiteFSNotRunningError message provides context."""
        detector = FakePrimaryDetector()
        detector.set_litefs_not_running()
        with pytest.raises(LiteFSNotRunningError, match="LiteFS.*not running"):
            detector.is_primary()
