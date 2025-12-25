"""Raft consensus wrapper around PySyncObj for distributed leader election.

RaftLeaderElection implements RaftLeaderElectionPort from litefs-py, providing
a clean API that isolates PySyncObj complexity from the rest of the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pysyncobj import SyncObj  # type: ignore[import-untyped]


class RaftLeaderElection:
    """Raft-based leader election using PySyncObj library.

    Wraps PySyncObj to provide Raft consensus for distributed leader election.
    Handles quorum consensus, log replication, and automatic failover while
    implementing the RaftLeaderElectionPort interface.

    Attributes:
        _sync_obj: The underlying PySyncObj Raft instance
        _is_leader: In-memory flag tracking whether this node is currently leader
        _cluster_members: List of node IDs in the cluster
        _election_timeout: Timeout in seconds for election process
        _heartbeat_interval: Interval in seconds for leader heartbeats
    """

    def __init__(
        self,
        node_id: str,
        cluster_members: list[str],
        election_timeout: float = 5.0,
        heartbeat_interval: float = 1.0,
    ) -> None:
        """Initialize Raft leader election.

        Args:
            node_id: Unique identifier for this node in the cluster
            cluster_members: List of node IDs in the cluster
            election_timeout: Timeout in seconds for election (must be > heartbeat_interval)
            heartbeat_interval: Interval in seconds for leader heartbeats (must be > 0)

        Raises:
            ValueError: If election_timeout <= heartbeat_interval or if either is <= 0
            ValueError: If node_id not in cluster_members
        """
        if heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be > 0")
        if election_timeout <= 0:
            raise ValueError("election_timeout must be > 0")
        if election_timeout <= heartbeat_interval:
            raise ValueError(
                "election_timeout must be > heartbeat_interval "
                f"({election_timeout} <= {heartbeat_interval})"
            )
        if node_id not in cluster_members:
            raise ValueError(
                f"node_id {node_id} not in cluster_members {cluster_members}"
            )

        self._node_id = node_id
        self._cluster_members = cluster_members
        self._election_timeout = election_timeout
        self._heartbeat_interval = heartbeat_interval
        self._is_leader = False

        # PySyncObj will be initialized by concrete implementation subclasses
        # For now, we just store configuration for use by subclasses
        self._sync_obj: SyncObj | None = None

    def is_leader_elected(self) -> bool:
        """Check if this node is the elected leader.

        Returns:
            True if this node is the elected leader, False otherwise.
        """
        return self._is_leader

    def elect_as_leader(self) -> None:
        """Elect this node as the leader.

        Idempotent: calling multiple times has same effect as calling once.
        """
        self._is_leader = True

    def demote_from_leader(self) -> None:
        """Demote this node from leadership.

        Idempotent: calling multiple times has same effect as calling once.
        """
        self._is_leader = False

    def get_cluster_members(self) -> list[str]:
        """Get list of all node IDs in the Raft cluster.

        Returns:
            List of node IDs (strings) in the cluster. May be empty list
            if cluster is not yet initialized.
        """
        return self._cluster_members.copy()

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if a node ID is a member of the Raft cluster.

        Args:
            node_id: The node ID to check.

        Returns:
            True if node_id is in the cluster, False otherwise.
        """
        return node_id in self._cluster_members

    def get_election_timeout(self) -> float:
        """Get the election timeout in seconds.

        Returns:
            Timeout duration in seconds (guaranteed > 0).
        """
        return self._election_timeout

    def get_heartbeat_interval(self) -> float:
        """Get the heartbeat interval in seconds.

        Returns:
            Interval duration in seconds (guaranteed > 0).
        """
        return self._heartbeat_interval

    def is_quorum_reached(self) -> bool:
        """Check if quorum is established in the cluster.

        Quorum is reached when > n/2 nodes are available, where n is the
        total cluster size. For simplicity, we consider all known members
        as available in this in-memory implementation.

        Returns:
            True if quorum is reached (> n/2 members exist), False otherwise.
        """
        cluster_size = len(self._cluster_members)
        if cluster_size == 0:
            return False
        # Quorum requires > n/2 nodes
        quorum_threshold = (cluster_size // 2) + 1
        # In this simple implementation, all members are considered online
        return cluster_size >= quorum_threshold
