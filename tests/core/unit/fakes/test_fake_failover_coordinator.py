"""Unit tests for FakeFailoverCoordinator."""

from __future__ import annotations

import pytest

from litefs.usecases.failover_coordinator import NodeState

from .fake_failover_coordinator import FakeFailoverCoordinator


@pytest.mark.unit
class TestFakeFailoverCoordinator:
    """Tests for FakeFailoverCoordinator fake implementation."""

    def test_initial_state_is_replica(self) -> None:
        """FakeFailoverCoordinator starts with REPLICA state by default."""
        fake = FakeFailoverCoordinator()
        assert fake.state == NodeState.REPLICA

    def test_get_state_returns_current_state(self) -> None:
        """state property returns the current configured state."""
        fake = FakeFailoverCoordinator()
        # Default
        assert fake.state == NodeState.REPLICA
        # After change
        fake.set_state(NodeState.PRIMARY)
        assert fake.state == NodeState.PRIMARY

    def test_set_state_to_primary(self) -> None:
        """set_state can transition to PRIMARY state."""
        fake = FakeFailoverCoordinator()
        fake.set_state(NodeState.PRIMARY)
        assert fake.state == NodeState.PRIMARY

    def test_set_state_to_replica(self) -> None:
        """set_state can transition to REPLICA state."""
        fake = FakeFailoverCoordinator(initial_state=NodeState.PRIMARY)
        fake.set_state(NodeState.REPLICA)
        assert fake.state == NodeState.REPLICA

    def test_multiple_state_transitions(self) -> None:
        """FakeFailoverCoordinator supports multiple state transitions."""
        fake = FakeFailoverCoordinator()
        assert fake.state == NodeState.REPLICA

        fake.set_state(NodeState.PRIMARY)
        assert fake.state == NodeState.PRIMARY

        fake.set_state(NodeState.REPLICA)
        assert fake.state == NodeState.REPLICA

        fake.set_state(NodeState.PRIMARY)
        assert fake.state == NodeState.PRIMARY

    def test_initial_state_can_be_overridden(self) -> None:
        """FakeFailoverCoordinator can be initialized with a specific state."""
        fake_primary = FakeFailoverCoordinator(initial_state=NodeState.PRIMARY)
        assert fake_primary.state == NodeState.PRIMARY

        fake_replica = FakeFailoverCoordinator(initial_state=NodeState.REPLICA)
        assert fake_replica.state == NodeState.REPLICA
