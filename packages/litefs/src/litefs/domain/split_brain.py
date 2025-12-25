"""Domain value objects for split-brain detection.

This module defines domain entities for representing Raft node states and
cluster states in a distributed system. These are used by the SplitBrainDetector
use case to detect and report split-brain scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class RaftNodeState:
    """Represents the state of a single node in a Raft cluster.

    Value object specifying a node's identity and leadership status.
    Immutable and hashable for use in collections.

    Attributes:
        node_id: Unique identifier for the node within the cluster.
                Must be non-empty and non-whitespace.
        is_leader: Boolean indicating whether this node is the elected leader
                  in the cluster.
    """

    node_id: str
    is_leader: bool

    def __post_init__(self) -> None:
        """Validate node state."""
        self._validate_node_id()

    def _validate_node_id(self) -> None:
        """Validate node_id is non-empty and non-whitespace-only."""
        if not self.node_id:
            raise LiteFSConfigError("node_id cannot be empty")

        if not self.node_id.strip():
            raise LiteFSConfigError("node_id cannot be whitespace-only")


@dataclass(frozen=True)
class RaftClusterState:
    """Represents the state of a Raft cluster.

    Value object specifying the complete state of all nodes in a cluster.
    Provides methods to query cluster topology and identify split-brain
    conditions (multiple nodes claiming leadership).

    Immutable and hashable for use in collections.

    Attributes:
        nodes: Non-empty list of RaftNodeState objects representing all nodes
               in the cluster. Must contain at least one node.

    Invariants:
        - nodes list is never empty
        - each node has a valid node_id
        - there should be at most one leader in a healthy cluster
    """

    nodes: list[RaftNodeState]

    def __post_init__(self) -> None:
        """Validate cluster state."""
        self._validate_nodes()

    def _validate_nodes(self) -> None:
        """Validate nodes list is non-empty."""
        if not self.nodes:
            raise LiteFSConfigError("nodes list cannot be empty")

    def count_leaders(self) -> int:
        """Count the number of nodes claiming leadership.

        Returns:
            The number of nodes with is_leader=True. In a healthy cluster,
            this should be exactly 1. Multiple leaders indicate a split-brain.
        """
        return sum(1 for node in self.nodes if node.is_leader)

    def has_single_leader(self) -> bool:
        """Check if exactly one node is the leader.

        Returns:
            True if exactly one node is the leader, False otherwise.
            False is returned when there are 0 or 2+ leaders.
        """
        return self.count_leaders() == 1

    def get_leader_nodes(self) -> list[RaftNodeState]:
        """Get all nodes that claim to be the leader.

        Returns:
            List of RaftNodeState objects with is_leader=True.
            May be empty if no leaders exist.
            May contain multiple nodes if split-brain is present.
        """
        return [node for node in self.nodes if node.is_leader]

    def get_replica_nodes(self) -> list[RaftNodeState]:
        """Get all nodes that are not leaders.

        Returns:
            List of RaftNodeState objects with is_leader=False.
        """
        return [node for node in self.nodes if not node.is_leader]
