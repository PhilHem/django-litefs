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
    based on the outcome of leader election. Integrates quorum-aware failover logic
    and health monitoring to ensure reliable leader election in Raft-based clusters.

    This use case is the central coordinator for RAFT-003 and handles:
    - Initial state determination from leader election port
    - Monitoring election status changes
    - Coordinating transitions between replica and primary states
    - Quorum-based failover (prevents split-brain scenarios)
    - Health-aware leadership (demotes unhealthy leaders)
    - Graceful handoff coordination
    - 3-node quorum consensus

    Dependencies:
        - LeaderElectionPort: Abstraction for leader election mechanism (static, RAFT, etc.)
        - RaftLeaderElectionPort (optional): For quorum-aware operations

    Thread safety:
        Reads from LeaderElectionPort which is responsible for synchronization.
        FailoverCoordinator maintains internal _healthy flag (should be synchronized
        externally if accessed from multiple threads).
    """

    def __init__(self, leader_election: LeaderElectionPort) -> None:
        """Initialize the failover coordinator.

        Determines initial state based on current election status from the
        leader election port. Starts in healthy state.

        Args:
            leader_election: Port implementation for leader election consensus.
        """
        self.leader_election = leader_election
        self._current_state = (
            NodeState.PRIMARY
            if leader_election.is_leader_elected()
            else NodeState.REPLICA
        )
        self._healthy = True

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

    def can_maintain_leadership(self) -> bool:
        """Check if this node can maintain leadership.

        Determines whether the node can safely continue as primary by checking:
        1. Current election status (must be elected leader)
        2. Quorum availability (if using RaftLeaderElectionPort)
        3. Health status (must be healthy)

        For Raft-based systems, this implements quorum-aware failover to prevent
        split-brain scenarios: a node cannot maintain leadership without quorum.

        Returns:
            True if this node can maintain leadership, False otherwise.
        """
        # Must be elected leader
        if not self.leader_election.is_leader_elected():
            return False

        # Must be healthy
        if not self._healthy:
            return False

        # Check quorum if available (Raft-based systems)
        return self._check_quorum()

    def can_become_leader(self) -> bool:
        """Check if this node can become the leader.

        Determines whether the node can safely transition to primary by checking:
        1. Health status (must be healthy)
        2. Quorum availability (if using RaftLeaderElectionPort)

        A node cannot become leader if:
        - It is unhealthy
        - Quorum is not available (in Raft systems)

        Returns:
            True if this node can become leader, False otherwise.
        """
        # Must be healthy
        if not self._healthy:
            return False

        # Check quorum if available (Raft-based systems)
        return self._check_quorum()

    def _check_quorum(self) -> bool:
        """Check if quorum is reached (if available).

        Returns True if quorum check is not available or if quorum is reached.
        Returns False if quorum check is available and quorum is not reached.

        Returns:
            True if quorum is available or not applicable, False if quorum lost.
        """
        if hasattr(self.leader_election, "is_quorum_reached"):
            election_obj = self.leader_election
            # attr-defined is safe due to hasattr check above
            is_quorum = getattr(election_obj, "is_quorum_reached")()
            return bool(is_quorum)
        return True

    def should_maintain_leadership(self) -> bool:
        """Determine if this node should continue as leader.

        Evaluates whether a currently primary node should remain primary.
        Unlike can_maintain_leadership(), this method includes health checks
        even if the node is currently elected.

        Returns:
            True if the node should maintain PRIMARY state, False if it should demote.
        """
        # If not currently primary, can't maintain what you don't have
        if self._current_state != NodeState.PRIMARY:
            return False

        # Check all failover conditions
        return self.can_maintain_leadership()

    def perform_graceful_handoff(self) -> None:
        """Perform graceful handoff of leadership.

        Coordinates the orderly transition from PRIMARY to REPLICA state
        when failover is necessary. This method:
        1. Verifies the node is currently PRIMARY
        2. Demotes from leader role
        3. Transitions to REPLICA state

        In Raft systems, this allows the node to gracefully step down
        without causing service disruption. The demote_from_leader() call
        on the election port signals to the cluster that this node will
        not run for re-election.
        """
        if self._current_state == NodeState.PRIMARY:
            self.leader_election.demote_from_leader()
            self._current_state = NodeState.REPLICA

    def mark_healthy(self) -> None:
        """Mark this node as healthy.

        Sets the node's health status to healthy. A healthy node can:
        - Become a leader candidate
        - Maintain current leadership (if quorum allows)

        This method should be called when the node recovers from an
        unhealthy state (e.g., database connection restored, disk space available).
        """
        self._healthy = True

    def mark_unhealthy(self) -> None:
        """Mark this node as unhealthy.

        Sets the node's health status to unhealthy. An unhealthy node:
        - Cannot become a leader
        - Should demote if currently primary (handled by caller)

        This method should be called when the node enters a degraded state
        (e.g., database connection lost, disk space critical, high latency).
        """
        self._healthy = False

    def is_healthy(self) -> bool:
        """Check if this node is healthy.

        Returns:
            True if the node is healthy, False if unhealthy.
        """
        return self._healthy
