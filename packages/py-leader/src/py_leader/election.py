"""RaftLeaderElection implementation using PySyncObj."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from py_leader._raft_node import LeaderElectionNode

if TYPE_CHECKING:
    from collections.abc import Callable


class RaftLeaderElectionError(Exception):
    """Base exception for RaftLeaderElection errors."""


class InvalidConfigurationError(RaftLeaderElectionError):
    """Raised when configuration is invalid."""


class RaftLeaderElection:
    """Implements RaftLeaderElectionPort using PySyncObj.

    This class provides a minimal Raft-based leader election mechanism.
    It does NOT provide replicated state - only leader election.

    The class implements the RaftLeaderElectionPort protocol from litefs-py,
    allowing it to be used as a drop-in replacement for static leader election.

    Example:
        >>> election = RaftLeaderElection(
        ...     node_id="node1",
        ...     cluster_members=["node1:20202", "node2:20202", "node3:20202"],
        ...     election_timeout=5.0,
        ...     heartbeat_interval=1.0,
        ... )
        >>> if election.is_leader_elected():
        ...     print("I am the leader!")
    """

    def __init__(
        self,
        node_id: str,
        cluster_members: list[str],
        election_timeout: float = 5.0,
        heartbeat_interval: float = 1.0,
        *,
        on_leader_change: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize the Raft leader election.

        Args:
            node_id: Unique identifier for this node. Must be one of the
                cluster members (the "host" part before the port).
            cluster_members: List of all cluster members in "host:port" format.
                Must include this node's address.
            election_timeout: Election timeout in seconds. Must be > 0 and
                greater than heartbeat_interval.
            heartbeat_interval: Heartbeat interval in seconds. Must be > 0.
            on_leader_change: Optional callback called when leadership changes.

        Raises:
            InvalidConfigurationError: If configuration is invalid.
        """
        self._validate_configuration(
            node_id, cluster_members, election_timeout, heartbeat_interval
        )

        self._node_id = node_id
        self._cluster_members = tuple(cluster_members)
        self._election_timeout = election_timeout
        self._heartbeat_interval = heartbeat_interval
        self._quorum_size = math.floor(len(cluster_members) / 2) + 1

        # Find this node's address in cluster members
        self_address = self._find_self_address(node_id, cluster_members)
        partners = [addr for addr in cluster_members if addr != self_address]

        self._node = LeaderElectionNode(
            self_address=self_address,
            partners=partners,
            election_timeout_ms=int(election_timeout * 1000),
            heartbeat_interval_ms=int(heartbeat_interval * 1000),
            on_leader_change=on_leader_change,
        )

    @staticmethod
    def _validate_configuration(
        node_id: str,
        cluster_members: list[str],
        election_timeout: float,
        heartbeat_interval: float,
    ) -> None:
        """Validate the configuration parameters.

        Raises:
            InvalidConfigurationError: If any parameter is invalid.
        """
        if not node_id or not node_id.strip():
            raise InvalidConfigurationError("node_id cannot be empty")

        if not cluster_members:
            raise InvalidConfigurationError("cluster_members cannot be empty")

        if len(cluster_members) < 2:
            raise InvalidConfigurationError(
                "cluster_members must have at least 2 nodes for Raft consensus"
            )

        # Check for duplicates
        if len(cluster_members) != len(set(cluster_members)):
            raise InvalidConfigurationError(
                "cluster_members contains duplicate addresses"
            )

        # Validate each member address format
        for member in cluster_members:
            if not member or ":" not in member:
                raise InvalidConfigurationError(
                    f"Invalid cluster member address: {member!r}. "
                    "Expected format: 'host:port'"
                )

        if election_timeout <= 0:
            raise InvalidConfigurationError("election_timeout must be > 0")

        if heartbeat_interval <= 0:
            raise InvalidConfigurationError("heartbeat_interval must be > 0")

        if heartbeat_interval >= election_timeout:
            raise InvalidConfigurationError(
                "heartbeat_interval must be less than election_timeout"
            )

    @staticmethod
    def _find_self_address(node_id: str, cluster_members: list[str]) -> str:
        """Find this node's address in the cluster members list.

        Args:
            node_id: The node ID to find.
            cluster_members: List of "host:port" addresses.

        Returns:
            The address matching the node_id.

        Raises:
            InvalidConfigurationError: If node_id not found in cluster.
        """
        for member in cluster_members:
            host = member.split(":")[0]
            if host == node_id:
                return member

        raise InvalidConfigurationError(
            f"node_id {node_id!r} not found in cluster_members. "
            f"Available hosts: {[m.split(':')[0] for m in cluster_members]}"
        )

    def is_leader_elected(self) -> bool:
        """Check if this node is the elected leader.

        Returns:
            True if this node is the elected leader, False otherwise.
        """
        return self._node.is_leader

    def elect_as_leader(self) -> None:
        """Request to become leader.

        Note: In Raft, you cannot force leadership. This is a no-op.
        Leadership is determined by consensus.
        """
        # No-op: Raft consensus decides leadership, not explicit requests

    def demote_from_leader(self) -> None:
        """Request to step down from leadership.

        Note: In Raft, you cannot force step-down without network partition.
        This is a no-op. The node will naturally lose leadership if it
        becomes partitioned or unhealthy.
        """
        # No-op: Raft consensus handles leadership transitions

    def get_cluster_members(self) -> list[str]:
        """Get list of all node addresses in the Raft cluster.

        Returns:
            List of node addresses (strings) in the cluster.
        """
        return list(self._cluster_members)

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if a node ID is a member of the Raft cluster.

        Args:
            node_id: The node ID (hostname part) to check.

        Returns:
            True if node_id is in the cluster, False otherwise.
        """
        for member in self._cluster_members:
            host = member.split(":")[0]
            if host == node_id:
                return True
        return False

    def get_election_timeout(self) -> float:
        """Get the election timeout in seconds.

        Returns:
            Timeout duration in seconds.
        """
        return self._election_timeout

    def get_heartbeat_interval(self) -> float:
        """Get the heartbeat interval in seconds.

        Returns:
            Interval duration in seconds.
        """
        return self._heartbeat_interval

    def is_quorum_reached(self) -> bool:
        """Check if quorum is established in the cluster.

        Quorum is reached when > n/2 nodes are responding,
        where n is the total cluster size.

        Returns:
            True if quorum is reached, False otherwise.
        """
        responding = self._node.get_responding_nodes_count()
        return responding >= self._quorum_size

    def destroy(self) -> None:
        """Cleanly shut down the Raft node.

        Should be called when the election is no longer needed.
        """
        self._node.destroy()
