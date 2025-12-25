"""FailoverCoordinator use case for orchestrating leader election and state transitions."""

from __future__ import annotations

from enum import Enum

from litefs.adapters.ports import LeaderElectionPort


class NodeState(Enum):
    """Enumeration of possible node states in the cluster.

    Attributes:
        PRIMARY: Node is the elected leader and can accept write operations.
        REPLICA: Node is a replica and can only accept read operations.
    """

    PRIMARY = "primary"
    REPLICA = "replica"


class FailoverCoordinator:
    """Coordinates leader election and state transitions between nodes.

    Orchestrates the failover process by monitoring election status and triggering
    appropriate state transitions. Maintains the current node state (PRIMARY or REPLICA)
    based on the outcome of leader election.

    This use case is the central coordinator for RAFT-003 and handles:
    - Initial state determination from leader election port
    - Monitoring election status changes
    - Coordinating transitions between replica and primary states
    - Exposing current node state to calling code

    Dependencies:
        - LeaderElectionPort: Abstraction for leader election mechanism (static, RAFT, etc.)

    Thread safety:
        Reads from LeaderElectionPort which is responsible for synchronization.
        FailoverCoordinator itself is stateless query interface.
    """

    def __init__(self, leader_election: LeaderElectionPort) -> None:
        """Initialize the failover coordinator.

        Determines initial state based on current election status from the
        leader election port.

        Args:
            leader_election: Port implementation for leader election consensus.
        """
        self.leader_election = leader_election
        self._current_state = (
            NodeState.PRIMARY
            if leader_election.is_leader_elected()
            else NodeState.REPLICA
        )

    @property
    def state(self) -> NodeState:
        """Get the current state of this node.

        Returns:
            NodeState.PRIMARY if this node is the elected leader,
            NodeState.REPLICA otherwise.
        """
        return self._current_state

    def coordinate_transition(self) -> None:
        """Coordinate a state transition based on current election status.

        Checks the current election status from the leader election port and
        performs any necessary state transitions. Transitions are idempotent:
        calling this method multiple times with the same election status has
        no additional effect beyond the first call.

        Transition rules:
            - If leader_election says elected AND current state is REPLICA -> PRIMARY
            - If leader_election says not elected AND current state is PRIMARY -> REPLICA
            - Otherwise, no transition needed (state matches election status)

        This method is safe to call repeatedly and forms the basis for
        polling-based failover coordination.
        """
        is_elected = self.leader_election.is_leader_elected()
        current_is_primary = self._current_state == NodeState.PRIMARY

        # Transition from REPLICA to PRIMARY
        if is_elected and not current_is_primary:
            self._current_state = NodeState.PRIMARY

        # Transition from PRIMARY to REPLICA
        elif not is_elected and current_is_primary:
            self._current_state = NodeState.REPLICA
