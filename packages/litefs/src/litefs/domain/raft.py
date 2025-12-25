"""Raft consensus configuration domain value objects."""

from dataclasses import dataclass

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class RaftSettings:
    """Raft cluster configuration.

    Value object specifying the configuration for Raft-based cluster membership
    and quorum calculation. Contains immutable settings for node identity and
    cluster topology.

    Attributes:
        node_id: Unique identifier for this node in the cluster.
                Must be non-empty, non-whitespace, and a member of cluster_members.
        cluster_members: Tuple of all node IDs in the cluster.
                        Must be non-empty, contain non-empty strings.
        quorum_size: Calculated as floor(n/2) + 1, where n is cluster size.
                    This ensures majority consensus for leader election.

    Invariants:
        - node_id must be in cluster_members
        - cluster_members must not be empty
        - quorum_size > n/2 (majority requirement)
    """

    node_id: str
    cluster_members: tuple[str, ...] | list[str]
    quorum_size: int = 0  # Will be calculated in __post_init__

    def __post_init__(self) -> None:
        """Validate Raft settings and calculate quorum size."""
        self._validate_node_id()
        self._validate_cluster_members()
        self._normalize_cluster_members()
        self._calculate_quorum_size()

    def _validate_node_id(self) -> None:
        """Validate node_id is non-empty and non-whitespace."""
        if not self.node_id:
            raise LiteFSConfigError("node_id cannot be empty")

        if not self.node_id.strip():
            raise LiteFSConfigError("node_id cannot be whitespace-only")

    def _validate_cluster_members(self) -> None:
        """Validate cluster_members list is non-empty and contains valid IDs."""
        if not self.cluster_members:
            raise LiteFSConfigError("cluster_members cannot be empty")

        # Check each member is non-empty and non-whitespace
        for member in self.cluster_members:
            if not member:
                raise LiteFSConfigError("cluster_members contains empty strings")

            if not member.strip():
                raise LiteFSConfigError(
                    "cluster_members contains whitespace-only strings"
                )

        # Check that node_id is in cluster_members
        if self.node_id not in self.cluster_members:
            raise LiteFSConfigError(
                f"node_id '{self.node_id}' must be a member of cluster_members"
            )

    def _normalize_cluster_members(self) -> None:
        """Convert cluster_members to tuple for immutability and hashing."""
        if isinstance(self.cluster_members, list):
            object.__setattr__(self, "cluster_members", tuple(self.cluster_members))

    def _calculate_quorum_size(self) -> None:
        """Calculate quorum size as floor(n/2) + 1.

        This ensures that a quorum is always a strict majority.
        For a 3-node cluster: floor(3/2) + 1 = 2 (need >1.5 nodes)
        For a 5-node cluster: floor(5/2) + 1 = 3 (need >2.5 nodes)
        """
        # We need to use object.__setattr__ because this is a frozen dataclass
        quorum = len(self.cluster_members) // 2 + 1
        object.__setattr__(self, "quorum_size", quorum)


@dataclass(frozen=True)
class QuorumPolicy:
    """Quorum and consensus timing configuration.

    Value object specifying timing parameters for Raft consensus protocol.
    Controls election timeouts and heartbeat intervals, which are critical
    for reliable leader election without spurious elections.

    Attributes:
        election_timeout_ms: Time (in milliseconds) a follower waits before
                            starting an election (e.g., 300-500ms).
                            Must be positive and > heartbeat_interval_ms.
        heartbeat_interval_ms: Time (in milliseconds) between heartbeat messages
                              from leader (e.g., 50-150ms).
                              Must be positive and < election_timeout_ms.

    Invariants:
        - Both timeouts must be positive integers (> 0)
        - heartbeat_interval_ms < election_timeout_ms (Raft requirement)
          Typical ratio is 5-10x (e.g., 100ms heartbeat, 500ms election)
    """

    election_timeout_ms: int
    heartbeat_interval_ms: int

    def __post_init__(self) -> None:
        """Validate quorum policy settings."""
        self._validate_election_timeout()
        self._validate_heartbeat_interval()
        self._validate_interval_relationship()

    def _validate_election_timeout(self) -> None:
        """Validate election_timeout_ms is positive."""
        if self.election_timeout_ms <= 0:
            raise LiteFSConfigError(
                f"election_timeout_ms must be positive, got: {self.election_timeout_ms}"
            )

    def _validate_heartbeat_interval(self) -> None:
        """Validate heartbeat_interval_ms is positive."""
        if self.heartbeat_interval_ms <= 0:
            raise LiteFSConfigError(
                f"heartbeat_interval_ms must be positive, got: {self.heartbeat_interval_ms}"
            )

    def _validate_interval_relationship(self) -> None:
        """Validate heartbeat_interval < election_timeout (Raft invariant).

        The heartbeat interval must be shorter than the election timeout
        to ensure that followers receive regular heartbeats and don't
        trigger spurious elections.
        """
        if self.heartbeat_interval_ms >= self.election_timeout_ms:
            raise LiteFSConfigError(
                f"heartbeat_interval_ms must be less than election_timeout_ms, "
                f"got: {self.heartbeat_interval_ms}ms vs {self.election_timeout_ms}ms"
            )
