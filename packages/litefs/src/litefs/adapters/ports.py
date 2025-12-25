"""Port interfaces for the LiteFS core package.

Ports define the contracts that adapters must implement.
These are Protocol classes (structural subtyping) for flexible testing.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class PrimaryDetectorPort(Protocol):
    """Port interface for primary node detection.

    Implementations check whether the current node is the primary (leader)
    in a LiteFS cluster. The primary node is the only one that can accept
    write operations.

    Contract:
        - is_primary() returns True if this node is primary, False if replica
        - May raise LiteFSNotRunningError if LiteFS is not available
    """

    def is_primary(self) -> bool:
        """Check if current node is primary.

        Returns:
            True if this node is primary (can accept writes),
            False if this node is a replica (read-only).

        Raises:
            LiteFSNotRunningError: If LiteFS is not running or mount path invalid.
        """
        ...


@runtime_checkable
class NodeIDResolverPort(Protocol):
    """Port interface for resolving the current node's ID/hostname.

    Implementations resolve how to identify the current node within a cluster.
    This enables testable abstraction of hostname resolution.

    Contract:
        - resolve_node_id() returns a non-empty string identifying this node
        - The returned string should be consistent across multiple calls
        - May raise KeyError if required configuration is missing
        - May raise ValueError if resolved ID is invalid (e.g., empty after stripping)
    """

    def resolve_node_id(self) -> str:
        """Resolve the current node's ID/hostname.

        Returns:
            A non-empty string uniquely identifying this node in the cluster.

        Raises:
            KeyError: If required environment variable or configuration is missing.
            ValueError: If the resolved ID is invalid (e.g., empty after stripping).
        """
        ...


@runtime_checkable
class LeaderElectionPort(Protocol):
    """Port interface for leader election coordination.

    Implementations handle the consensus mechanism for electing a leader node.
    Abstracts the underlying election algorithm (static, RAFT, etc.) from the
    coordinator that needs to orchestrate state transitions.

    Contract:
        - is_leader_elected() returns True if this node is the elected leader
        - elect_as_leader() performs leader election and updates state
        - demote_from_leader() removes this node from leadership
        - All methods are idempotent (multiple calls have same effect as one)
    """

    def is_leader_elected(self) -> bool:
        """Check if this node is the elected leader.

        Returns:
            True if this node is the elected leader, False otherwise.
        """
        ...

    def elect_as_leader(self) -> None:
        """Elect this node as the leader.

        Idempotent: calling multiple times has same effect as calling once.
        """
        ...

    def demote_from_leader(self) -> None:
        """Demote this node from leadership.

        Idempotent: calling multiple times has same effect as calling once.
        """
        ...


@runtime_checkable
class RaftLeaderElectionPort(LeaderElectionPort, Protocol):
    """Port interface for Raft-based leader election.

    Extends LeaderElectionPort with Raft-specific cluster management and
    consensus operations. Abstracts Raft consensus details for use by
    coordinators and primary election logic.

    Contract:
        - get_cluster_members() returns list of node IDs in the cluster
        - is_member_in_cluster(node_id) checks if node is in the cluster
        - get_election_timeout() returns timeout in seconds (must be > 0)
        - get_heartbeat_interval() returns interval in seconds (must be > 0)
        - is_quorum_reached() returns True if quorum is established
        - Heartbeat interval must always be less than election timeout
        - All list returns must not be None
    """

    def get_cluster_members(self) -> list[str]:
        """Get list of all node IDs in the Raft cluster.

        Returns:
            List of node IDs (strings) in the cluster. May be empty list
            if cluster is not yet initialized.
        """
        ...

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if a node ID is a member of the Raft cluster.

        Args:
            node_id: The node ID to check.

        Returns:
            True if node_id is in the cluster, False otherwise.
        """
        ...

    def get_election_timeout(self) -> float:
        """Get the election timeout in seconds.

        The election timeout is the duration a follower waits before
        considering itself eligible to become a candidate. Must be greater
        than heartbeat_interval to avoid unnecessary elections.

        Returns:
            Timeout duration in seconds (must be > 0).
        """
        ...

    def get_heartbeat_interval(self) -> float:
        """Get the heartbeat interval in seconds.

        The heartbeat interval is how often the leader sends heartbeat
        messages to maintain leadership. Must be less than election_timeout
        to ensure reliable consensus without spurious elections.

        Returns:
            Interval duration in seconds (must be > 0).
        """
        ...

    def is_quorum_reached(self) -> bool:
        """Check if quorum is established in the cluster.

        Quorum is reached when > n/2 nodes are responding/available,
        where n is the total cluster size. This is required for any
        leader election or log replication.

        Returns:
            True if quorum is reached, False otherwise.
        """
        ...


class EnvironmentNodeIDResolver:
    """Default implementation: resolve node ID from LITEFS_NODE_ID environment variable.

    Reads the LITEFS_NODE_ID environment variable and returns it after stripping
    whitespace. This is the standard way to configure node identity in containerized
    deployments.
    """

    def resolve_node_id(self) -> str:
        """Resolve node ID from LITEFS_NODE_ID environment variable.

        Returns:
            The value of LITEFS_NODE_ID after stripping whitespace.

        Raises:
            KeyError: If LITEFS_NODE_ID environment variable is not set.
            ValueError: If LITEFS_NODE_ID is empty or whitespace-only after stripping.
        """
        node_id = os.environ["LITEFS_NODE_ID"]
        node_id_stripped = node_id.strip()

        if not node_id_stripped:
            raise ValueError("node ID cannot be empty or whitespace-only")

        return node_id_stripped
