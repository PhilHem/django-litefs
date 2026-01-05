"""Fake adapters for core unit testing.

These in-memory fakes replace real implementations that require I/O
(filesystem, network) for fast, isolated unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


class FakeRaftLeaderElection:
    """In-memory fake for RaftLeaderElectionPort - no network access.

    Use this instead of the real RaftLeaderElection in unit tests for:
    - Faster test execution (no network I/O)
    - No PySyncObj dependency required
    - Stateful testing (toggle leadership during test)

    Implements RaftLeaderElectionPort protocol for type safety.

    Example:
        def test_split_brain_detection(fake_raft_election):
            fake_raft_election.set_leader(True)
            fake_raft_election.set_cluster_members(["node1:20202", "node2:20202"])
            adapter = SplitBrainDetectorAdapter(
                raft_election=fake_raft_election,
                this_node_id="node1",
            )
    """

    def __init__(
        self,
        *,
        is_leader: bool = False,
        cluster_members: list[str] | None = None,
        election_timeout: float = 5.0,
        heartbeat_interval: float = 1.0,
        quorum_reached: bool = True,
    ) -> None:
        """Initialize with desired state.

        Args:
            is_leader: Whether this node is the leader. Defaults to False.
            cluster_members: List of cluster members in "host:port" format.
                           Defaults to a 3-node cluster.
            election_timeout: Election timeout in seconds.
            heartbeat_interval: Heartbeat interval in seconds.
            quorum_reached: Whether quorum is reached.
        """
        self._is_leader = is_leader
        self._cluster_members = cluster_members or [
            "node1:20202",
            "node2:20202",
            "node3:20202",
        ]
        self._election_timeout = election_timeout
        self._heartbeat_interval = heartbeat_interval
        self._quorum_reached = quorum_reached

    def is_leader_elected(self) -> bool:
        """Return configured leader state.

        Returns:
            True if this node is the leader, False otherwise.
        """
        return self._is_leader

    def elect_as_leader(self) -> None:
        """No-op in fake. State is controlled via set_leader()."""
        pass

    def demote_from_leader(self) -> None:
        """No-op in fake. State is controlled via set_leader()."""
        pass

    def get_cluster_members(self) -> list[str]:
        """Return configured cluster members.

        Returns:
            List of cluster member addresses in "host:port" format.
        """
        return list(self._cluster_members)

    def is_member_in_cluster(self, node_id: str) -> bool:
        """Check if a node is in the cluster.

        Args:
            node_id: The node ID (hostname) to check.

        Returns:
            True if the node is in the cluster, False otherwise.
        """
        for member in self._cluster_members:
            host = member.split(":")[0]
            if host == node_id:
                return True
        return False

    def get_election_timeout(self) -> float:
        """Return configured election timeout.

        Returns:
            Election timeout in seconds.
        """
        return self._election_timeout

    def get_heartbeat_interval(self) -> float:
        """Return configured heartbeat interval.

        Returns:
            Heartbeat interval in seconds.
        """
        return self._heartbeat_interval

    def is_quorum_reached(self) -> bool:
        """Return configured quorum state.

        Returns:
            True if quorum is reached, False otherwise.
        """
        return self._quorum_reached

    # Test helpers

    def set_leader(self, is_leader: bool) -> None:
        """Set leader state for testing.

        Args:
            is_leader: New leader state.
        """
        self._is_leader = is_leader

    def set_cluster_members(self, members: list[str]) -> None:
        """Set cluster members for testing.

        Args:
            members: New list of cluster members.
        """
        self._cluster_members = members

    def set_quorum_reached(self, reached: bool) -> None:
        """Set quorum state for testing.

        Args:
            reached: Whether quorum is reached.
        """
        self._quorum_reached = reached


@dataclass
class FakeHttpResponse:
    """Fake HTTP response for testing."""

    status_code: int = 200
    json_data: dict | None = None
    raise_error: Exception | None = None

    def json(self) -> dict:
        """Return configured JSON data.

        Raises:
            ValueError: If json_data is None.
        """
        if self.json_data is None:
            raise ValueError("No JSON data")
        return self.json_data


@dataclass
class FakeHttpxClient:
    """In-memory fake for httpx.Client - no network access.

    Use this instead of real httpx.Client in unit tests for:
    - Faster test execution (no network I/O)
    - Predictable responses (configure what each URL returns)
    - Error injection (simulate network failures)

    Example:
        def test_remote_node_query():
            client = FakeHttpxClient()
            client.add_response(
                "http://node2:8080/health/status",
                {"is_leader": True}
            )
            adapter = SplitBrainDetectorAdapter(..., client=client)
    """

    responses: dict[str, FakeHttpResponse] = field(default_factory=dict)
    default_response: FakeHttpResponse | None = None
    requests_made: list[str] = field(default_factory=list)

    def get(self, url: str, **kwargs) -> FakeHttpResponse:
        """Simulate HTTP GET request.

        Args:
            url: The URL to request.
            **kwargs: Ignored (timeout, headers, etc.)

        Returns:
            Configured FakeHttpResponse for the URL.

        Raises:
            httpx.ConnectError: If no response configured and no default.
        """
        self.requests_made.append(url)

        if url in self.responses:
            response = self.responses[url]
            if response.raise_error:
                raise response.raise_error
            return response

        if self.default_response is not None:
            if self.default_response.raise_error:
                raise self.default_response.raise_error
            return self.default_response

        raise httpx.ConnectError(f"No response configured for {url}")

    def add_response(
        self,
        url: str,
        json_data: dict | None = None,
        status_code: int = 200,
        error: Exception | None = None,
    ) -> None:
        """Add a response for a URL.

        Args:
            url: The URL to respond to.
            json_data: JSON data to return.
            status_code: HTTP status code.
            error: Exception to raise instead of returning response.
        """
        self.responses[url] = FakeHttpResponse(
            status_code=status_code,
            json_data=json_data,
            raise_error=error,
        )

    def set_default_response(
        self,
        json_data: dict | None = None,
        status_code: int = 200,
        error: Exception | None = None,
    ) -> None:
        """Set the default response for unconfigured URLs.

        Args:
            json_data: JSON data to return.
            status_code: HTTP status code.
            error: Exception to raise instead of returning response.
        """
        self.default_response = FakeHttpResponse(
            status_code=status_code,
            json_data=json_data,
            raise_error=error,
        )

    def __enter__(self) -> "FakeHttpxClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        pass
