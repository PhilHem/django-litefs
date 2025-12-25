"""Factory functions for creating leader election instances.

Provides factory methods to instantiate leader election implementations
from settings. Handles optional dependency imports gracefully.
"""

from __future__ import annotations

from litefs.domain.settings import LiteFSSettings
from litefs.adapters.ports import RaftLeaderElectionPort


class PyLeaderNotInstalledError(ImportError):
    """Raised when py-leader is required but not installed.

    Install with: pip install litefs-py[raft]
    """

    def __init__(self) -> None:
        super().__init__(
            "py-leader is not installed. "
            "Install with: pip install litefs-py[raft]"
        )


def create_raft_leader_election(
    settings: LiteFSSettings,
    node_id: str,
    election_timeout: float = 5.0,
    heartbeat_interval: float = 1.0,
) -> RaftLeaderElectionPort:
    """Create a RaftLeaderElection instance from LiteFSSettings.

    Factory function that creates a RaftLeaderElection (from py-leader)
    configured using the Raft settings from LiteFSSettings.

    Args:
        settings: LiteFSSettings configured for Raft leader election.
                 Must have leader_election="raft" with valid raft_self_addr and raft_peers.
        node_id: Unique identifier for this node in the cluster.
        election_timeout: Timeout in seconds for election (default 5.0, must be > heartbeat_interval).
        heartbeat_interval: Interval in seconds for leader heartbeats (default 1.0, must be > 0).

    Returns:
        A RaftLeaderElectionPort implementation (RaftLeaderElection from py-leader).

    Raises:
        PyLeaderNotInstalledError: If py-leader is not installed.
        ValueError: If settings.leader_election != "raft" or required Raft config is missing.
        ValueError: If election_timeout <= heartbeat_interval or if either is <= 0.
        ValueError: If node_id not in cluster_members.

    Example:
        >>> settings = LiteFSSettings(
        ...     mount_path="/litefs",
        ...     data_path="/data",
        ...     database_name="app.db",
        ...     leader_election="raft",
        ...     proxy_addr="localhost:8080",
        ...     enabled=True,
        ...     retention="24h",
        ...     raft_self_addr="node1:20202",
        ...     raft_peers=["node2:20202", "node3:20202"],
        ... )
        >>> election = create_raft_leader_election(settings, node_id="node1:20202")
    """
    # Validate settings is configured for Raft
    if settings.leader_election != "raft":
        raise ValueError(
            f"settings.leader_election must be 'raft', got: {settings.leader_election}"
        )

    if settings.raft_self_addr is None:
        raise ValueError("settings.raft_self_addr is required for Raft leader election")

    if settings.raft_peers is None:
        raise ValueError("settings.raft_peers is required for Raft leader election")

    # Build cluster members list: self + peers
    cluster_members = [settings.raft_self_addr, *settings.raft_peers]

    # Import py-leader (optional dependency)
    try:
        from py_leader import RaftLeaderElection  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PyLeaderNotInstalledError() from exc

    # RaftLeaderElection implements RaftLeaderElectionPort
    result: RaftLeaderElectionPort = RaftLeaderElection(
        node_id=node_id,
        cluster_members=cluster_members,
        election_timeout=election_timeout,
        heartbeat_interval=heartbeat_interval,
    )
    return result
