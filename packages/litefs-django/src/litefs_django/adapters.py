"""Adapter implementations for the LiteFS Django package.

Contains adapter classes that implement ports defined in litefs.adapters.ports.
These adapters are Django-specific implementations used for leader election
and other cluster coordination.
"""

from __future__ import annotations

from litefs.adapters.ports import LeaderElectionPort
from litefs.usecases.primary_initializer import PrimaryInitializer


class StaticLeaderElection(LeaderElectionPort):
    """Static leader election implementation for predefined primary nodes.

    Implements LeaderElectionPort for static mode where the primary node is
    determined by configuration rather than consensus. Uses PrimaryInitializer
    to check if this node is the configured primary.

    This is suitable for:
    - Single-node deployments
    - Deployments with a fixed primary (e.g., node1 is always primary)
    - Testing and development environments

    Thread safety:
        - All methods are read-only and safe for concurrent calls
        - State is immutable after construction

    Example:
        >>> from litefs.usecases.primary_initializer import PrimaryInitializer
        >>> initializer = PrimaryInitializer(static_config)
        >>> election = StaticLeaderElection(initializer, "node1")
        >>> election.is_leader_elected()
        True
    """

    def __init__(self, initializer: PrimaryInitializer, node_id: str) -> None:
        """Initialize static leader election.

        Args:
            initializer: PrimaryInitializer configured with static leader config.
            node_id: The ID of the current node in the cluster.
        """
        self._initializer = initializer
        self._node_id = node_id

    def is_leader_elected(self) -> bool:
        """Check if this node is the elected leader.

        Returns:
            True if this node is the configured primary, False otherwise.
        """
        return self._initializer.is_primary(self._node_id)

    def elect_as_leader(self) -> None:
        """No-op for static mode.

        Static mode does not support dynamic leader election.
        The leader is determined by configuration.
        """
        pass

    def demote_from_leader(self) -> None:
        """No-op for static mode.

        Static mode does not support dynamic demotion.
        The leader is determined by configuration.
        """
        pass
