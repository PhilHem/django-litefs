"""Thin adapter wrapping Raft leader election for abstract port interface.

This adapter implements LeaderElectionPort and RaftLeaderElectionPort
by wrapping a concrete RaftLeaderElectionPort implementation (e.g., from py-leader).
It ensures the core package never imports py-leader directly, maintaining
Clean Architecture principles where the core layer depends on abstractions,
not concrete implementations.
"""

from __future__ import annotations

from litefs.adapters.ports import RaftLeaderElectionPort


class RaftLeaderElectionAdapter:
    """Thin adapter implementing LeaderElectionPort and RaftLeaderElectionPort.

    Wraps a concrete RaftLeaderElectionPort implementation and delegates all
    method calls to it. This adapter enables dependency inversion: the core
    package depends only on the port abstraction, not on specific Raft
    implementations (py-leader, etc.).

    Constructor injection pattern:
        adapter = RaftLeaderElectionAdapter(raft_election_impl)

    Clean Architecture:
        - No direct imports of py-leader or pysyncobj
        - Pure delegation - no business logic
        - Converts implementation details to abstract interface
    """

    def __init__(self, raft_port: RaftLeaderElectionPort) -> None:
        """Initialize adapter with a RaftLeaderElectionPort implementation.

        Args:
            raft_port: Concrete implementation of RaftLeaderElectionPort to wrap.

        Raises:
            TypeError: If raft_port is not provided.
        """
        self._raft_port = raft_port

    def is_leader_elected(self) -> bool:
        """Check if this node is the elected leader.

        Delegates to wrapped port.

        Returns:
            True if this node is the elected leader, False otherwise.
        """
        return self._raft_port.is_leader_elected()

    def elect_as_leader(self) -> None:
        """Elect this node as the leader.

        Delegates to wrapped port. Idempotent operation.
        """
        self._raft_port.elect_as_leader()

    def demote_from_leader(self) -> None:
        """Demote this node from leadership.

        Delegates to wrapped port. Idempotent operation.
        """
        self._raft_port.demote_from_leader()

    def get_cluster_members(self) -> list[str]:
        """Get list of all node IDs in the Raft cluster.

        Delegates to wrapped port.

        Returns:
            List of node IDs (strings) in the cluster.
        """
        return self._raft_port.get_cluster_members()

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if a node ID is a member of the Raft cluster.

        Delegates to wrapped port.

        Args:
            node_id: The node ID to check.

        Returns:
            True if node_id is in the cluster, False otherwise.
        """
        return self._raft_port.is_member_in_cluster(node_id)

    def get_election_timeout(self) -> float:
        """Get the election timeout in seconds.

        Delegates to wrapped port.

        Returns:
            Timeout duration in seconds (must be > 0).
        """
        return self._raft_port.get_election_timeout()

    def get_heartbeat_interval(self) -> float:
        """Get the heartbeat interval in seconds.

        Delegates to wrapped port.

        Returns:
            Interval duration in seconds (must be > 0).
        """
        return self._raft_port.get_heartbeat_interval()

    def is_quorum_reached(self) -> bool:
        """Check if quorum is established in the cluster.

        Delegates to wrapped port.

        Returns:
            True if quorum is reached, False otherwise.
        """
        return self._raft_port.is_quorum_reached()
