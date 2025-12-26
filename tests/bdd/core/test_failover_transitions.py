"""BDD step definitions for failover_transitions.feature.

Tests the FailoverCoordinator use case for state transitions between
PRIMARY and REPLICA states based on leader election, health, and quorum.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

from litefs.domain.events import FailoverEvent, FailoverEventType
from litefs.usecases.failover_coordinator import FailoverCoordinator, NodeState

# Type alias for BDD context dict
Context = dict[str, Any]


# ----- Mock classes (reused from test_failover_coordinator.py pattern) -----


class MockLeaderElectionPort:
    """Mock implementation of LeaderElectionPort for testing."""

    def __init__(self, is_elected: bool = False) -> None:
        """Initialize mock with election result."""
        self.is_elected = is_elected
        self.elect_called = False
        self.demote_called = False

    def is_leader_elected(self) -> bool:
        """Return mock election status."""
        return self.is_elected

    def elect_as_leader(self) -> None:
        """Record election call."""
        self.elect_called = True
        self.is_elected = True

    def demote_from_leader(self) -> None:
        """Record demotion call."""
        self.demote_called = True
        self.is_elected = False


class MockRaftLeaderElectionPort(MockLeaderElectionPort):
    """Mock implementation of RaftLeaderElectionPort for testing."""

    def __init__(
        self,
        is_elected: bool = False,
        cluster_members: list[str] | None = None,
        quorum_reached: bool = True,
    ) -> None:
        """Initialize mock with Raft-specific settings."""
        super().__init__(is_elected=is_elected)
        self.cluster_members = cluster_members or ["node1", "node2", "node3"]
        self.quorum_reached = quorum_reached

    def get_cluster_members(self) -> list[str]:
        """Return cluster members."""
        return self.cluster_members

    def is_quorum_reached(self) -> bool:
        """Return quorum status."""
        return self.quorum_reached


class MockEventEmitter:
    """Mock implementation of EventEmitterPort for testing."""

    def __init__(self) -> None:
        """Initialize with empty event list."""
        self.events: list[FailoverEvent] = []

    def emit(self, event: FailoverEvent) -> None:
        """Record emitted event."""
        self.events.append(event)

    def clear(self) -> None:
        """Clear recorded events."""
        self.events.clear()


class FakeLoggingAdapter:
    """Fake logging adapter for testing."""

    def __init__(self) -> None:
        """Initialize with empty warnings list."""
        self._warnings: list[str] = []

    def warning(self, message: str) -> None:
        """Store a warning message."""
        self._warnings.append(message)

    @property
    def warnings(self) -> list[str]:
        """Get a copy of captured warning messages."""
        return list(self._warnings)

    def clear(self) -> None:
        """Clear all captured warning messages."""
        self._warnings.clear()


# ----- Scenarios (linked to feature file) -----


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Replica is promoted when elected and healthy",
)
def test_replica_promoted_when_elected_and_healthy() -> None:
    """Test replica promotion when elected and healthy."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Primary maintains leadership when conditions are met",
)
def test_primary_maintains_leadership() -> None:
    """Test primary maintains leadership when conditions met."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Primary performs graceful handoff on demotion request",
)
def test_graceful_handoff() -> None:
    """Test graceful handoff on demotion request."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Unhealthy replica cannot be promoted",
)
def test_unhealthy_replica_cannot_be_promoted() -> None:
    """Test unhealthy replica cannot be promoted."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Primary demotes when marked unhealthy",
)
def test_primary_demotes_when_unhealthy() -> None:
    """Test primary demotes when marked unhealthy."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Replica cannot be promoted without quorum",
)
def test_replica_cannot_be_promoted_without_quorum() -> None:
    """Test replica cannot be promoted without quorum."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Primary demotes when quorum is lost",
)
def test_primary_demotes_when_quorum_lost() -> None:
    """Test primary demotes when quorum is lost."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
@scenario(
    "../../features/core/failover_transitions.feature",
    "Repeated promotion attempts are idempotent",
)
def test_repeated_promotion_idempotent() -> None:
    """Test repeated promotion attempts are idempotent."""
    pass


# ----- Fixtures -----


@pytest.fixture
def context() -> Context:
    """Shared context for passing state between steps."""
    return {
        "leader_election": MockRaftLeaderElectionPort(
            is_elected=False, quorum_reached=True
        ),
        "event_emitter": MockEventEmitter(),
        "logger": FakeLoggingAdapter(),
        "coordinator": None,
    }


# ----- Background step -----


@given("a 3-node LiteFS cluster with Raft consensus")
def given_3_node_cluster(context: Context) -> None:
    """Set up a 3-node cluster."""
    context["leader_election"].cluster_members = ["node1", "node2", "node3"]


# ----- Node state steps -----


@given("a replica node")
def given_replica_node(context: Context) -> None:
    """Ensure the node is in REPLICA state."""
    context["leader_election"].is_elected = False
    context["coordinator"] = FailoverCoordinator(
        leader_election=context["leader_election"],
        event_emitter=context["event_emitter"],
        logger=context["logger"],
    )


@given("a primary node")
def given_primary_node(context: Context) -> None:
    """Ensure the node is in PRIMARY state."""
    context["leader_election"].is_elected = True
    context["coordinator"] = FailoverCoordinator(
        leader_election=context["leader_election"],
        event_emitter=context["event_emitter"],
        logger=context["logger"],
    )
    context["event_emitter"].clear()  # Clear any initial events


# ----- Health steps -----


@given("the node is marked healthy")
def given_node_healthy(context: Context) -> None:
    """Mark the node as healthy."""
    if context["coordinator"]:
        context["coordinator"].mark_healthy()


@given("the node is marked unhealthy")
def given_node_unhealthy(context: Context) -> None:
    """Mark the node as unhealthy."""
    if context["coordinator"]:
        context["coordinator"].mark_unhealthy()


@when("the node is marked unhealthy")
def when_node_unhealthy(context: Context) -> None:
    """Mark the node as unhealthy."""
    context["coordinator"].mark_unhealthy()


# ----- Quorum steps -----


@given("quorum is reached")
def given_quorum_reached(context: Context) -> None:
    """Ensure quorum is reached."""
    context["leader_election"].quorum_reached = True


@given("quorum is NOT reached due to network partition")
def given_quorum_not_reached(context: Context) -> None:
    """Simulate network partition - quorum not reached."""
    context["leader_election"].quorum_reached = False


@given("quorum was previously reached")
def given_quorum_previously_reached(context: Context) -> None:
    """Record that quorum was previously reached."""
    context["leader_election"].quorum_reached = True


@when("quorum is lost due to network partition")
def when_quorum_lost(context: Context) -> None:
    """Simulate quorum loss due to network partition."""
    context["leader_election"].quorum_reached = False


# ----- Leader election steps -----


@given("leader election completes with this node as leader")
def given_election_completes_as_leader(context: Context) -> None:
    """Simulate leader election completing with this node as leader."""
    context["leader_election"].elect_as_leader()


@given("leader election confirms this node as leader")
def given_election_confirms_leader(context: Context) -> None:
    """Confirm this node remains the leader."""
    context["leader_election"].is_elected = True


@when("leader election completes with this node as leader")
def when_election_completes_as_leader(context: Context) -> None:
    """Simulate leader election completing and coordinate transition."""
    context["leader_election"].elect_as_leader()
    # Check if we can become leader before transitioning
    if context["coordinator"].can_become_leader():
        context["coordinator"].coordinate_transition()


# ----- Action steps -----


@when("failover coordination runs")
def when_failover_coordination_runs(context: Context) -> None:
    """Run failover coordination with health/quorum guards.

    This implements the full coordination logic:
    - PRIMARY nodes demote if unhealthy or quorum lost
    - REPLICA nodes only promote if can_become_leader() passes
    """
    coord = context["coordinator"]
    is_elected = context["leader_election"].is_leader_elected()

    # Check leadership conditions for PRIMARYs
    if coord.state == NodeState.PRIMARY:
        if not coord.is_healthy():
            coord.demote_for_health()
        elif not coord.can_maintain_leadership():
            coord.demote_for_quorum_loss()
        else:
            coord.coordinate_transition()
    # For REPLICAs trying to become PRIMARY, guard with can_become_leader
    elif coord.state == NodeState.REPLICA and is_elected:
        if coord.can_become_leader():
            coord.coordinate_transition()
        # else: stay REPLICA (warnings already logged by can_become_leader)
    else:
        coord.coordinate_transition()


@when("failover coordination runs multiple times")
def when_failover_coordination_runs_multiple_times(context: Context) -> None:
    """Run failover coordination multiple times."""
    context["event_emitter"].clear()
    for _ in range(5):
        context["coordinator"].coordinate_transition()


@when("graceful handoff is requested")
def when_graceful_handoff_requested(context: Context) -> None:
    """Request graceful handoff."""
    context["coordinator"].perform_graceful_handoff()


# ----- State assertion steps -----


@then("the node state transitions to PRIMARY")
def then_state_is_primary(context: Context) -> None:
    """Assert node state is PRIMARY."""
    assert context["coordinator"].state == NodeState.PRIMARY, (
        f"Expected PRIMARY, got {context['coordinator'].state}"
    )


@then("the node state remains PRIMARY")
def then_state_remains_primary(context: Context) -> None:
    """Assert node state remains PRIMARY."""
    assert context["coordinator"].state == NodeState.PRIMARY, (
        f"Expected PRIMARY, got {context['coordinator'].state}"
    )


@then("the node state transitions to REPLICA")
def then_state_is_replica(context: Context) -> None:
    """Assert node state is REPLICA."""
    assert context["coordinator"].state == NodeState.REPLICA, (
        f"Expected REPLICA, got {context['coordinator'].state}"
    )


@then("the node state remains REPLICA")
def then_state_remains_replica(context: Context) -> None:
    """Assert node state remains REPLICA."""
    assert context["coordinator"].state == NodeState.REPLICA, (
        f"Expected REPLICA, got {context['coordinator'].state}"
    )


# ----- Capability assertion steps -----


@then("the node can accept write operations")
def then_node_can_write(context: Context) -> None:
    """Assert node is in PRIMARY state (can accept writes)."""
    assert context["coordinator"].state == NodeState.PRIMARY, (
        "Only PRIMARY can accept writes"
    )


# ----- Graceful handoff steps -----


@then("pending writes are completed")
def then_pending_writes_completed(context: Context) -> None:
    """Assert graceful handoff started (demote_from_leader called)."""
    assert context["leader_election"].demote_called, (
        "demote_from_leader should be called"
    )


@then("leadership is released to the cluster")
def then_leadership_released(context: Context) -> None:
    """Assert leadership was released."""
    assert context["leader_election"].is_elected is False, (
        "Node should no longer be leader"
    )


# ----- Warning assertion steps -----


@then("a warning is logged about health blocking promotion")
def then_health_warning_logged(context: Context) -> None:
    """Assert a warning about health blocking promotion was logged."""
    warnings = context["logger"].warnings
    assert len(warnings) >= 1, f"Expected warning, got {warnings}"
    health_warning = any("unhealthy" in w.lower() for w in warnings)
    assert health_warning, f"Expected health warning, got: {warnings}"


@then("a warning is logged about quorum blocking promotion")
def then_quorum_warning_logged(context: Context) -> None:
    """Assert a warning about quorum blocking promotion was logged."""
    warnings = context["logger"].warnings
    assert len(warnings) >= 1, f"Expected warning, got {warnings}"
    quorum_warning = any("quorum" in w.lower() for w in warnings)
    assert quorum_warning, f"Expected quorum warning, got: {warnings}"


# ----- Event assertion steps -----


@then("a health-triggered demotion event is emitted")
def then_health_demotion_event(context: Context) -> None:
    """Assert HEALTH_DEMOTION event was emitted."""
    health_events = [
        e
        for e in context["event_emitter"].events
        if e.event_type == FailoverEventType.HEALTH_DEMOTION
    ]
    assert len(health_events) >= 1, (
        f"Expected HEALTH_DEMOTION event, got: {context['event_emitter'].events}"
    )


@then("a quorum-loss demotion event is emitted")
def then_quorum_loss_demotion_event(context: Context) -> None:
    """Assert QUORUM_LOSS_DEMOTION event was emitted."""
    quorum_events = [
        e
        for e in context["event_emitter"].events
        if e.event_type == FailoverEventType.QUORUM_LOSS_DEMOTION
    ]
    assert len(quorum_events) >= 1, (
        f"Expected QUORUM_LOSS_DEMOTION event, got: {context['event_emitter'].events}"
    )


@then("no redundant state change events are emitted")
def then_no_redundant_events(context: Context) -> None:
    """Assert no redundant events were emitted during idempotent transitions."""
    assert len(context["event_emitter"].events) == 0, (
        f"Expected no events, got: {context['event_emitter'].events}"
    )
