"""HTTPX-based implementation of the SplitBrainDetectorPort.

This adapter queries all nodes in a Raft cluster to determine their leadership
status, enabling split-brain detection. For this node, it uses the local
RaftLeaderElectionPort. For other nodes, it makes HTTP requests to their
health endpoints.
"""

from __future__ import annotations

import httpx

from litefs.adapters.ports import RaftLeaderElectionPort, SplitBrainDetectorPort
from litefs.domain.split_brain import RaftClusterState, RaftNodeState


class SplitBrainDetectorAdapter:
    """HTTPX-based adapter for split-brain detection across cluster nodes.

    Queries all nodes in the cluster to determine their leadership status.
    For the local node, uses the RaftLeaderElectionPort directly.
    For remote nodes, makes HTTP requests to their health endpoints.

    The health endpoint must return JSON with at minimum:
        {"is_leader": bool}

    This adapter implements SplitBrainDetectorPort for use by the
    SplitBrainDetector use case.
    """

    def __init__(
        self,
        raft_election: RaftLeaderElectionPort,
        this_node_id: str,
        *,
        health_endpoint_path: str = "/health/status",
        health_endpoint_port: int = 8080,
        connect_timeout: float = 2.0,
        read_timeout: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the split-brain detector adapter.

        Args:
            raft_election: RaftLeaderElectionPort for local node queries and
                          getting cluster members.
            this_node_id: ID of this node (hostname part of cluster member).
            health_endpoint_path: URL path for health endpoint. Defaults to
                                 "/health/status".
            health_endpoint_port: Port for health endpoint HTTP server.
                                 Defaults to 8080.
            connect_timeout: Connection timeout in seconds. Defaults to 2.0.
            read_timeout: Read timeout in seconds. Defaults to 5.0.
            client: Optional httpx.Client for dependency injection (testing).
        """
        self._raft_election = raft_election
        self._this_node_id = this_node_id
        self._health_endpoint_path = health_endpoint_path
        self._health_endpoint_port = health_endpoint_port
        self._timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        self._client = client

    def get_cluster_state(self) -> RaftClusterState:
        """Get the current state of all nodes in the cluster.

        Queries each cluster member for their leadership status.
        For this node, uses local Raft state directly.
        For other nodes, makes HTTP requests to their health endpoints.

        Returns:
            RaftClusterState containing all nodes and their leadership status.

        Note:
            If a remote node is unreachable, it is assumed to be a non-leader.
            This is a conservative assumption - an unreachable node cannot
            cause split-brain issues since it can't accept writes.
        """
        cluster_members = self._raft_election.get_cluster_members()
        node_states: list[RaftNodeState] = []

        for member in cluster_members:
            node_id = self._extract_node_id(member)

            if node_id == self._this_node_id:
                # Use local Raft state for this node
                is_leader = self._raft_election.is_leader_elected()
            else:
                # Query remote node's health endpoint
                is_leader = self._query_remote_node_leadership(member)

            node_states.append(RaftNodeState(node_id=node_id, is_leader=is_leader))

        return RaftClusterState(nodes=node_states)

    def _extract_node_id(self, member: str) -> str:
        """Extract node ID (hostname) from cluster member address.

        Args:
            member: Cluster member in "host:port" format.

        Returns:
            The hostname part of the address.
        """
        return member.split(":")[0]

    def _query_remote_node_leadership(self, member: str) -> bool:
        """Query a remote node's health endpoint to determine leadership.

        Args:
            member: Cluster member in "host:port" format.

        Returns:
            True if the node claims to be leader, False otherwise.
            Returns False if the node is unreachable or returns invalid data.
        """
        node_id = self._extract_node_id(member)
        url = (
            f"http://{node_id}:{self._health_endpoint_port}{self._health_endpoint_path}"
        )

        try:
            if self._client is not None:
                response = self._client.get(url, timeout=self._timeout)
            else:
                with httpx.Client() as client:
                    response = client.get(url, timeout=self._timeout)

            if response.status_code == 200:
                data = response.json()
                return bool(data.get("is_leader", False))

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError, KeyError):
            # Network error, HTTP error, or invalid JSON - assume not leader
            pass

        return False


# Runtime protocol check
assert isinstance(
    SplitBrainDetectorAdapter.__new__(SplitBrainDetectorAdapter),
    SplitBrainDetectorPort,
), "SplitBrainDetectorAdapter must implement SplitBrainDetectorPort"
