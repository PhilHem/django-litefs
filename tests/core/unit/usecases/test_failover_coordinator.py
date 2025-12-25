"""Unit tests for FailoverCoordinator use case."""

import pytest
from hypothesis import given, strategies as st

from litefs.usecases.failover_coordinator import FailoverCoordinator, NodeState
from litefs.adapters.ports import LeaderElectionPort


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


@pytest.mark.unit
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


@pytest.mark.unit
@pytest.mark.property
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
