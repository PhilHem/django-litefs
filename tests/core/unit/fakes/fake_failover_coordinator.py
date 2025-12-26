"""Fake implementation of FailoverCoordinator for testing.

This module provides an in-memory fake for testing components that depend on
FailoverCoordinator without needing actual leader election infrastructure.
"""

from __future__ import annotations

from litefs.usecases.failover_coordinator import NodeState


class FakeFailoverCoordinator:
    """In-memory fake for FailoverCoordinator - no real leader election.

    Use this instead of mocking FailoverCoordinator in unit tests for:
    - Faster test execution (no leader election I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (configure node state during test)
    - State transition testing (simulate failover scenarios)

    Provides a simplified interface focused on state management for testing.
    Does not implement the full FailoverCoordinator protocol - only the
    essential state property and set_state method for test control.

    Example:
        def test_database_backend_on_replica(fake_failover_coordinator):
            fake_failover_coordinator.set_state(NodeState.REPLICA)
            backend = LiteFSBackend(coordinator=fake_failover_coordinator)
            with pytest.raises(NotPrimaryError):
                backend.execute_write("INSERT ...")
    """

    def __init__(self, initial_state: NodeState | None = None) -> None:
        """Initialize with desired state.

        Args:
            initial_state: Initial node state. Defaults to NodeState.REPLICA.
        """
        self._state: NodeState = (
            initial_state if initial_state is not None else NodeState.REPLICA
        )

    @property
    def state(self) -> NodeState:
        """Get the current state of this node.

        Returns:
            Current NodeState (PRIMARY or REPLICA).
        """
        return self._state

    def set_state(self, state: NodeState) -> None:
        """Set the node state for testing.

        Args:
            state: New node state to set.
        """
        self._state = state
