"""Unit tests for FailoverCoordinator use case."""

import pytest
from hypothesis import given, strategies as st

from litefs.usecases.failover_coordinator import FailoverCoordinator, NodeState
from litefs.adapters.ports import LeaderElectionPort
from litefs.domain.events import FailoverEvent, FailoverEventType


class MockLoggingPort:
    """Mock implementation of LoggingPort for testing."""

    def __init__(self) -> None:
        """Initialize with empty warnings list."""
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        """Record warning message."""
        self.warnings.append(message)

    def clear(self) -> None:
        """Clear recorded warnings."""
        self.warnings.clear()


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


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestFailoverCoordinator:
    """Test FailoverCoordinator use case."""

    def test_initial_state_is_replica_when_not_elected(self) -> None:
        """Test that initial state is REPLICA when not elected."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.REPLICA

    def test_initial_state_is_primary_when_elected(self) -> None:
        """Test that initial state is PRIMARY when elected."""
        port = MockLeaderElectionPort(is_elected=True)
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.PRIMARY

    def test_transition_to_primary_when_elected(self) -> None:
        """Test replica -> primary transition when elected."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)
        assert coordinator.state == NodeState.REPLICA

        # Simulate election
        port.elect_as_leader()
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.PRIMARY
        assert port.elect_called is True

    def test_transition_to_replica_when_demoted(self) -> None:
        """Test primary -> replica transition when demoted."""
        port = MockLeaderElectionPort(is_elected=True)
        coordinator = FailoverCoordinator(leader_election=port)
        assert coordinator.state == NodeState.PRIMARY

        # Simulate demotion
        port.demote_from_leader()
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.REPLICA
        assert port.demote_called is True

    def test_no_transition_when_state_unchanged(self) -> None:
        """Test that no transition occurs when state doesn't change."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)
        initial_state = coordinator.state

        # Call transition with same state
        coordinator.coordinate_transition()

        assert coordinator.state == initial_state
        # Port methods should not be called
        assert port.elect_called is False
        assert port.demote_called is False

    def test_idempotent_transition_to_primary(self) -> None:
        """Test that repeated transitions to primary are idempotent."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)

        # First transition to primary
        port.elect_as_leader()
        coordinator.coordinate_transition()
        first_state = coordinator.state

        # Reset mock call tracking
        port.elect_called = False

        # Second transition - should be idempotent
        coordinator.coordinate_transition()
        second_state = coordinator.state

        assert first_state == second_state == NodeState.PRIMARY
        # Port.elect_as_leader should not be called again
        assert port.elect_called is False

    def test_idempotent_transition_to_replica(self) -> None:
        """Test that repeated transitions to replica are idempotent."""
        port = MockLeaderElectionPort(is_elected=True)
        coordinator = FailoverCoordinator(leader_election=port)

        # First transition to replica
        port.demote_from_leader()
        coordinator.coordinate_transition()
        first_state = coordinator.state

        # Reset mock call tracking
        port.demote_called = False

        # Second transition - should be idempotent
        coordinator.coordinate_transition()
        second_state = coordinator.state

        assert first_state == second_state == NodeState.REPLICA
        # Port.demote_from_leader should not be called again
        assert port.demote_called is False

    def test_state_property_returns_current_state(self) -> None:
        """Test that state property always returns current state."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)

        # Query state multiple times
        state1 = coordinator.state
        state2 = coordinator.state
        state3 = coordinator.state

        assert state1 == state2 == state3 == NodeState.REPLICA

    def test_multiple_state_transitions_sequence(self) -> None:
        """Test sequence of state transitions."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)
        assert coordinator.state == NodeState.REPLICA

        # Transition: replica -> primary
        port.elect_as_leader()
        coordinator.coordinate_transition()
        assert coordinator.state == NodeState.PRIMARY

        # Transition: primary -> replica
        port.demote_from_leader()
        coordinator.coordinate_transition()
        assert coordinator.state == NodeState.REPLICA

        # Transition: replica -> primary (again)
        port.elect_as_leader()
        coordinator.coordinate_transition()
        assert coordinator.state == NodeState.PRIMARY

    def test_state_consistency_with_election_port(self) -> None:
        """Test that coordinator state stays consistent with election port."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)

        # State should match port
        assert coordinator.state == NodeState.REPLICA
        assert port.is_leader_elected() is False

        # After election
        port.elect_as_leader()
        coordinator.coordinate_transition()
        assert coordinator.state == NodeState.PRIMARY
        assert port.is_leader_elected() is True

    def test_uses_leader_election_port_abstraction(self) -> None:
        """Test that FailoverCoordinator uses LeaderElectionPort abstraction."""
        port = MockLeaderElectionPort(is_elected=False)
        coordinator = FailoverCoordinator(leader_election=port)

        # Coordinator should rely on port interface, not implementation
        assert isinstance(port, LeaderElectionPort) or hasattr(
            port, "is_leader_elected"
        )
        coordinator.coordinate_transition()
        # Should execute without errors


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
        self.election_timeout = 5.0
        self.heartbeat_interval = 1.0

    def get_cluster_members(self) -> list[str]:
        """Return cluster members."""
        return self.cluster_members

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if node is in cluster."""
        return node_id in self.cluster_members

    def get_election_timeout(self) -> float:
        """Return election timeout in seconds."""
        return self.election_timeout

    def get_heartbeat_interval(self) -> float:
        """Return heartbeat interval in seconds."""
        return self.heartbeat_interval

    def is_quorum_reached(self) -> bool:
        """Return quorum status."""
        return self.quorum_reached


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestFailoverCoordinatorQuorum:
    """Test FailoverCoordinator quorum-aware failover logic."""

    def test_primary_stays_leader_with_quorum(self) -> None:
        """Test that PRIMARY remains leader when quorum is reached."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.PRIMARY
        assert coordinator.can_maintain_leadership() is True

    def test_primary_demotes_without_quorum(self) -> None:
        """Test that PRIMARY node demotes when quorum is lost."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=False)
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.PRIMARY
        assert coordinator.can_maintain_leadership() is False

    def test_replica_cannot_become_leader_without_quorum(self) -> None:
        """Test that REPLICA cannot be elected without quorum."""
        port = MockRaftLeaderElectionPort(
            is_elected=False, quorum_reached=False
        )
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.REPLICA
        assert coordinator.can_become_leader() is False

    def test_replica_can_become_leader_with_quorum(self) -> None:
        """Test that REPLICA can be elected when quorum is reached."""
        port = MockRaftLeaderElectionPort(
            is_elected=False, quorum_reached=True
        )
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.REPLICA
        assert coordinator.can_become_leader() is True

    def test_failover_triggered_by_quorum_loss(self) -> None:
        """Test failover coordination when quorum is lost during leadership."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        coordinator = FailoverCoordinator(leader_election=port)
        assert coordinator.state == NodeState.PRIMARY

        # Simulate quorum loss
        port.quorum_reached = False

        # Trigger failover check
        should_demote = not coordinator.can_maintain_leadership()
        assert should_demote is True

    def test_three_node_cluster_quorum_calculation(self) -> None:
        """Test quorum behavior in 3-node cluster."""
        # 3-node cluster requires quorum of 2 (floor(3/2) + 1)
        port = MockRaftLeaderElectionPort(
            cluster_members=["node1", "node2", "node3"],
            is_elected=True,
            quorum_reached=True,
        )
        coordinator = FailoverCoordinator(leader_election=port)

        assert len(port.get_cluster_members()) == 3
        assert coordinator.can_maintain_leadership() is True

    def test_graceful_handoff_coordinates_demotion(self) -> None:
        """Test graceful handoff coordination during demotion."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        coordinator = FailoverCoordinator(leader_election=port)

        # Simulate graceful handoff: verify quorum before demoting
        if not coordinator.can_maintain_leadership():
            coordinator.perform_graceful_handoff()

        # With quorum, we shouldn't need handoff
        port.quorum_reached = False
        if not coordinator.can_maintain_leadership():
            coordinator.perform_graceful_handoff()
            assert coordinator.state == NodeState.REPLICA

    def test_network_partition_demotion(self) -> None:
        """Test that node demotes when it loses network connectivity (quorum lost)."""
        # Start with node as PRIMARY with quorum
        port = MockRaftLeaderElectionPort(
            is_elected=True, quorum_reached=True
        )
        coordinator = FailoverCoordinator(leader_election=port)
        assert coordinator.state == NodeState.PRIMARY

        # Simulate network partition: quorum lost
        port.quorum_reached = False
        assert coordinator.can_maintain_leadership() is False


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestFailoverCoordinatorHealthIntegration:
    """Test FailoverCoordinator health-aware failover logic."""

    def test_unhealthy_node_cannot_be_primary(self) -> None:
        """Test that unhealthy nodes cannot become primary."""
        port = MockRaftLeaderElectionPort(
            is_elected=False, quorum_reached=True
        )
        coordinator = FailoverCoordinator(leader_election=port)

        # Mark as unhealthy
        coordinator.mark_unhealthy()

        assert coordinator.is_healthy() is False
        assert coordinator.can_become_leader() is False

    def test_healthy_node_can_become_primary(self) -> None:
        """Test that healthy nodes can become primary when eligible."""
        port = MockRaftLeaderElectionPort(
            is_elected=False, quorum_reached=True
        )
        coordinator = FailoverCoordinator(leader_election=port)

        # Ensure healthy
        coordinator.mark_healthy()

        assert coordinator.is_healthy() is True
        assert coordinator.can_become_leader() is True

    def test_primary_demotes_when_becoming_unhealthy(self) -> None:
        """Test that PRIMARY demotes when becoming unhealthy."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        coordinator = FailoverCoordinator(leader_election=port)

        assert coordinator.state == NodeState.PRIMARY
        assert coordinator.is_healthy() is True

        # Node becomes unhealthy
        coordinator.mark_unhealthy()

        assert coordinator.is_healthy() is False
        # Should trigger demotion check
        assert coordinator.should_maintain_leadership() is False

    def test_health_status_persists_across_state_transitions(self) -> None:
        """Test that health status is maintained across state changes."""
        port = MockRaftLeaderElectionPort(is_elected=False, quorum_reached=True)
        coordinator = FailoverCoordinator(leader_election=port)

        # Set unhealthy
        coordinator.mark_unhealthy()
        initial_health = coordinator.is_healthy()

        # Transition state
        coordinator.coordinate_transition()

        # Health status should persist
        assert coordinator.is_healthy() == initial_health


@pytest.mark.tier(3)
@pytest.mark.tra("UseCase")
class TestFailoverCoordinatorPBT:
    """Property-based tests for FailoverCoordinator."""

    @given(initial_election=st.booleans())
    def test_initial_state_matches_election_status(
        self, initial_election: bool
    ) -> None:
        """PBT: Initial state should match election status."""
        port = MockLeaderElectionPort(is_elected=initial_election)
        coordinator = FailoverCoordinator(leader_election=port)

        expected_state = NodeState.PRIMARY if initial_election else NodeState.REPLICA
        assert coordinator.state == expected_state

    @given(
        initial_elected=st.booleans(),
        transition_sequence=st.lists(st.booleans(), min_size=1, max_size=10),
    )
    def test_state_transitions_form_valid_paths(
        self, initial_elected: bool, transition_sequence: list[bool]
    ) -> None:
        """PBT: State transitions should always result in valid node states."""
        port = MockLeaderElectionPort(is_elected=initial_elected)
        coordinator = FailoverCoordinator(leader_election=port)

        # Verify initial state is valid
        assert coordinator.state in (NodeState.PRIMARY, NodeState.REPLICA)

        # Apply sequence of transitions
        for should_be_leader in transition_sequence:
            port.is_elected = should_be_leader
            coordinator.coordinate_transition()

            # State should always be valid
            assert coordinator.state in (NodeState.PRIMARY, NodeState.REPLICA)
            # State should match port status
            expected_state = (
                NodeState.PRIMARY if should_be_leader else NodeState.REPLICA
            )
            assert coordinator.state == expected_state

    def test_transition_idempotence(self) -> None:
        """PBT: Repeated transitions with same election status should be idempotent."""
        # Test with various election states
        for initial_elected in [True, False]:
            port = MockLeaderElectionPort(is_elected=initial_elected)
            coordinator = FailoverCoordinator(leader_election=port)

            initial_state = coordinator.state

            # Call coordinate_transition multiple times without changing port
            for _ in range(5):
                coordinator.coordinate_transition()

            assert coordinator.state == initial_state

    @given(elected_state=st.booleans())
    def test_state_query_consistency(self, elected_state: bool) -> None:
        """PBT: Querying state multiple times should return consistent results."""
        port = MockLeaderElectionPort(is_elected=elected_state)
        coordinator = FailoverCoordinator(leader_election=port)

        # Query state multiple times
        states = [coordinator.state for _ in range(10)]

        # All queries should return the same state
        assert all(s == states[0] for s in states)
        # State should match elected status
        expected_state = NodeState.PRIMARY if elected_state else NodeState.REPLICA
        assert states[0] == expected_state

    @given(
        cluster_size=st.integers(min_value=1, max_value=9),
        is_elected=st.booleans(),
        quorum_reached=st.booleans(),
    )
    def test_quorum_election_invariants(
        self, cluster_size: int, is_elected: bool, quorum_reached: bool
    ) -> None:
        """PBT: Quorum constraints should always be satisfied."""
        cluster_members = [f"node{i}" for i in range(cluster_size)]
        port = MockRaftLeaderElectionPort(
            cluster_members=cluster_members,
            is_elected=is_elected,
            quorum_reached=quorum_reached,
        )
        coordinator = FailoverCoordinator(leader_election=port)

        # Invariant: can only be PRIMARY if elected
        if coordinator.state == NodeState.PRIMARY:
            assert is_elected is True

        # Invariant: cannot maintain leadership without quorum
        can_maintain = coordinator.can_maintain_leadership()
        if is_elected:
            assert can_maintain == quorum_reached

    @given(
        cluster_size=st.integers(min_value=1, max_value=9),
        health_states=st.lists(st.booleans(), min_size=1, max_size=5),
    )
    def test_health_state_invariants(
        self, cluster_size: int, health_states: list[bool]
    ) -> None:
        """PBT: Health state invariants should hold across transitions."""
        cluster_members = [f"node{i}" for i in range(cluster_size)]
        port = MockRaftLeaderElectionPort(cluster_members=cluster_members)
        coordinator = FailoverCoordinator(leader_election=port)

        # Apply health state changes
        for is_healthy in health_states:
            if is_healthy:
                coordinator.mark_healthy()
            else:
                coordinator.mark_unhealthy()

            # Invariant: unhealthy nodes cannot be PRIMARY
            if not coordinator.is_healthy():
                assert coordinator.can_become_leader() is False


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
class TestFailoverCoordinatorEventEmission:
    """Test FailoverCoordinator event emission functionality."""

    def test_event_emitter_is_optional(self) -> None:
        """Test that event_emitter is optional (backward compatible)."""
        port = MockLeaderElectionPort(is_elected=False)
        # Should work without event_emitter
        coordinator = FailoverCoordinator(leader_election=port)
        coordinator.coordinate_transition()
        assert coordinator.state == NodeState.REPLICA

    def test_event_emitted_on_replica_to_primary_transition(self) -> None:
        """Test that PROMOTED_TO_PRIMARY event is emitted on replica -> primary."""
        port = MockLeaderElectionPort(is_elected=False)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.REPLICA

        # Trigger transition
        port.elect_as_leader()
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.PRIMARY
        assert len(emitter.events) == 1
        assert emitter.events[0].event_type == FailoverEventType.PROMOTED_TO_PRIMARY

    def test_event_emitted_on_primary_to_replica_transition(self) -> None:
        """Test that DEMOTED_TO_REPLICA event is emitted on primary -> replica."""
        port = MockLeaderElectionPort(is_elected=True)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.PRIMARY
        emitter.clear()  # Clear initial state events if any

        # Trigger transition
        port.demote_from_leader()
        coordinator.coordinate_transition()

        assert coordinator.state == NodeState.REPLICA
        assert len(emitter.events) == 1
        assert emitter.events[0].event_type == FailoverEventType.DEMOTED_TO_REPLICA

    def test_health_demotion_emits_specific_event(self) -> None:
        """Test that health-triggered demotion emits HEALTH_DEMOTION event."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.PRIMARY
        emitter.clear()

        # Mark unhealthy and trigger health-aware demotion
        coordinator.mark_unhealthy()
        coordinator.demote_for_health()

        assert coordinator.state == NodeState.REPLICA
        # Should have HEALTH_DEMOTION event
        health_events = [
            e for e in emitter.events
            if e.event_type == FailoverEventType.HEALTH_DEMOTION
        ]
        assert len(health_events) == 1

    def test_quorum_loss_demotion_emits_specific_event(self) -> None:
        """Test that quorum-loss demotion emits QUORUM_LOSS_DEMOTION event."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.PRIMARY
        emitter.clear()

        # Lose quorum and trigger quorum-aware demotion
        port.quorum_reached = False
        coordinator.demote_for_quorum_loss()

        assert coordinator.state == NodeState.REPLICA
        # Should have QUORUM_LOSS_DEMOTION event
        quorum_events = [
            e for e in emitter.events
            if e.event_type == FailoverEventType.QUORUM_LOSS_DEMOTION
        ]
        assert len(quorum_events) == 1

    def test_no_duplicate_events_on_repeated_transitions(self) -> None:
        """Test that no duplicate events are emitted on idempotent transitions."""
        port = MockLeaderElectionPort(is_elected=False)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        emitter.clear()

        # Call coordinate_transition multiple times without state change
        for _ in range(5):
            coordinator.coordinate_transition()

        # No events should be emitted since state didn't change
        assert len(emitter.events) == 0

    def test_graceful_handoff_emits_event(self) -> None:
        """Test that graceful handoff emits GRACEFUL_HANDOFF event."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.PRIMARY
        emitter.clear()

        # Perform graceful handoff
        coordinator.perform_graceful_handoff()

        assert coordinator.state == NodeState.REPLICA
        # Should have GRACEFUL_HANDOFF event
        handoff_events = [
            e for e in emitter.events
            if e.event_type == FailoverEventType.GRACEFUL_HANDOFF
        ]
        assert len(handoff_events) == 1

    def test_no_event_when_graceful_handoff_from_replica(self) -> None:
        """Test that graceful handoff from REPLICA state emits no event."""
        port = MockLeaderElectionPort(is_elected=False)
        emitter = MockEventEmitter()
        coordinator = FailoverCoordinator(leader_election=port, event_emitter=emitter)
        assert coordinator.state == NodeState.REPLICA
        emitter.clear()

        # Attempt graceful handoff from replica (no-op)
        coordinator.perform_graceful_handoff()

        # No events should be emitted
        assert len(emitter.events) == 0
        assert coordinator.state == NodeState.REPLICA


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.FailoverCoordinator")
class TestFailoverCoordinatorLogging:
    """Test FailoverCoordinator logging functionality."""

    def test_logger_is_optional(self) -> None:
        """Test that logger is optional (backward compatible)."""
        port = MockLeaderElectionPort(is_elected=False)
        # Should work without logger
        coordinator = FailoverCoordinator(leader_election=port)
        coordinator.mark_unhealthy()
        coordinator.can_become_leader()
        # No exception raised

    def test_no_logging_when_logger_is_none(self) -> None:
        """Test that no logging occurs when logger is None."""
        port = MockRaftLeaderElectionPort(is_elected=False, quorum_reached=False)
        coordinator = FailoverCoordinator(leader_election=port, logger=None)
        coordinator.mark_unhealthy()

        # Should not raise even though health and quorum would block
        result = coordinator.can_become_leader()
        assert result is False

    def test_logger_warning_on_health_blocks_can_become_leader(self) -> None:
        """Test that warning is logged when health blocks can_become_leader."""
        port = MockRaftLeaderElectionPort(is_elected=False, quorum_reached=True)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        # Mark unhealthy
        coordinator.mark_unhealthy()
        result = coordinator.can_become_leader()

        assert result is False
        assert len(logger.warnings) == 1
        assert "unhealthy" in logger.warnings[0].lower()
        assert "leader" in logger.warnings[0].lower()

    def test_logger_warning_on_quorum_blocks_can_become_leader(self) -> None:
        """Test that warning is logged when quorum blocks can_become_leader."""
        port = MockRaftLeaderElectionPort(is_elected=False, quorum_reached=False)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        # Node is healthy but quorum not reached
        result = coordinator.can_become_leader()

        assert result is False
        assert len(logger.warnings) == 1
        assert "quorum" in logger.warnings[0].lower()

    def test_logger_warning_on_health_blocks_can_maintain_leadership(self) -> None:
        """Test that warning is logged when health blocks can_maintain_leadership."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        # Mark unhealthy
        coordinator.mark_unhealthy()
        result = coordinator.can_maintain_leadership()

        assert result is False
        assert len(logger.warnings) == 1
        assert "unhealthy" in logger.warnings[0].lower()
        assert "maintain" in logger.warnings[0].lower() or "leader" in logger.warnings[0].lower()

    def test_logger_warning_on_quorum_blocks_can_maintain_leadership(self) -> None:
        """Test that warning is logged when quorum blocks can_maintain_leadership."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=False)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        result = coordinator.can_maintain_leadership()

        assert result is False
        assert len(logger.warnings) == 1
        assert "quorum" in logger.warnings[0].lower()

    def test_no_warning_when_can_become_leader_succeeds(self) -> None:
        """Test that no warning is logged when can_become_leader succeeds."""
        port = MockRaftLeaderElectionPort(is_elected=False, quorum_reached=True)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        result = coordinator.can_become_leader()

        assert result is True
        assert len(logger.warnings) == 0

    def test_no_warning_when_can_maintain_leadership_succeeds(self) -> None:
        """Test that no warning is logged when can_maintain_leadership succeeds."""
        port = MockRaftLeaderElectionPort(is_elected=True, quorum_reached=True)
        logger = MockLoggingPort()
        coordinator = FailoverCoordinator(leader_election=port, logger=logger)

        result = coordinator.can_maintain_leadership()

        assert result is True
        assert len(logger.warnings) == 0
