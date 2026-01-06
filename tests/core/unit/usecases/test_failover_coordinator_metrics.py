"""Tests for FailoverCoordinator metrics integration."""

from __future__ import annotations

import pytest

from litefs.usecases.failover_coordinator import FailoverCoordinator, NodeState
from litefs.adapters.fakes.fake_metrics import FakeMetricsAdapter


class FakeLeaderElection:
    """Minimal fake for LeaderElectionPort."""

    def __init__(self, is_leader: bool = False) -> None:
        self._is_leader = is_leader

    def is_leader_elected(self) -> bool:
        return self._is_leader

    def elect_as_leader(self) -> None:
        self._is_leader = True

    def demote_from_leader(self) -> None:
        self._is_leader = False

    def set_leader_status(self, is_leader: bool) -> None:
        """Test helper to change leader status."""
        self._is_leader = is_leader


@pytest.mark.unit
class TestFailoverCoordinatorMetricsInit:
    """Tests for FailoverCoordinator metrics on initialization."""

    def test_sets_initial_node_state_metric_primary(self) -> None:
        """Should set node state metric to PRIMARY on init if elected."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=True)

        FailoverCoordinator(leader_election=election, metrics=metrics)

        assert metrics.current_node_state is True

    def test_sets_initial_node_state_metric_replica(self) -> None:
        """Should set node state metric to REPLICA on init if not elected."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=False)

        FailoverCoordinator(leader_election=election, metrics=metrics)

        assert metrics.current_node_state is False

    def test_sets_initial_leader_elected_metric(self) -> None:
        """Should set leader elected metric on init."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=True)

        FailoverCoordinator(leader_election=election, metrics=metrics)

        assert metrics.current_leader_elected is True


@pytest.mark.unit
class TestFailoverCoordinatorMetricsTransitions:
    """Tests for FailoverCoordinator metrics during state transitions."""

    def test_updates_metrics_on_promotion_to_primary(self) -> None:
        """Should update metrics when transitioning from REPLICA to PRIMARY."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=False)
        coordinator = FailoverCoordinator(leader_election=election, metrics=metrics)

        assert coordinator.state == NodeState.REPLICA
        metrics.clear_calls()

        # Simulate election win
        election.set_leader_status(True)
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.PRIMARY
        assert metrics.current_node_state is True
        assert metrics.current_leader_elected is True

    def test_updates_metrics_on_demotion_to_replica(self) -> None:
        """Should update metrics when transitioning from PRIMARY to REPLICA."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=True)
        coordinator = FailoverCoordinator(leader_election=election, metrics=metrics)

        assert coordinator.state == NodeState.PRIMARY
        metrics.clear_calls()

        # Simulate election loss
        election.set_leader_status(False)
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.REPLICA
        assert metrics.current_node_state is False
        assert metrics.current_leader_elected is False

    def test_no_metric_update_when_no_state_change(self) -> None:
        """Should not update metrics if state doesn't change."""
        metrics = FakeMetricsAdapter()
        election = FakeLeaderElection(is_leader=True)
        coordinator = FailoverCoordinator(leader_election=election, metrics=metrics)

        metrics.clear_calls()

        # No state change - still elected
        coordinator.coordinate_transition()

        # No additional metric calls since state didn't change
        assert len(metrics.calls) == 0


@pytest.mark.unit
class TestFailoverCoordinatorMetricsOptional:
    """Tests for FailoverCoordinator without metrics."""

    def test_works_without_metrics(self) -> None:
        """Should work correctly when metrics not provided."""
        election = FakeLeaderElection(is_leader=True)
        coordinator = FailoverCoordinator(leader_election=election)

        # Should not raise
        assert coordinator.state == NodeState.PRIMARY

    def test_transitions_work_without_metrics(self) -> None:
        """State transitions should work without metrics."""
        election = FakeLeaderElection(is_leader=False)
        coordinator = FailoverCoordinator(leader_election=election)

        election.set_leader_status(True)
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.PRIMARY
