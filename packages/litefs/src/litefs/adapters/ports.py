"""Port interfaces for the LiteFS core package.

Ports define the contracts that adapters must implement.
These are Protocol classes (structural subtyping) for flexible testing.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from litefs.domain.binary import BinaryLocation, BinaryMetadata, Platform
    from litefs.domain.events import FailoverEvent
    from litefs.domain.split_brain import RaftClusterState


@dataclass(frozen=True)
class ForwardingResult:
    """Result of forwarding a request to the primary node.

    Immutable value object containing the response from the primary.

    Attributes:
        status_code: HTTP status code from the primary's response.
        headers: Response headers from the primary.
        body: Response body bytes from the primary.
    """

    status_code: int
    headers: dict[str, str]
    body: bytes


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


@runtime_checkable
class SplitBrainDetectorPort(Protocol):
    """Port interface for split-brain detection.

    Implementations provide cluster state information that allows the
    SplitBrainDetector use case to identify when multiple nodes claim
    leadership (split-brain scenario).

    A split-brain occurs when network partition causes cluster consensus
    to break down, resulting in multiple nodes believing they are the leader.
    This port allows detection of such scenarios so applications can take
    corrective action (e.g., demoting extra leaders, alerting operators).

    Contract:
        - get_cluster_state() returns a RaftClusterState with all node states
        - The RaftClusterState must contain valid node leadership information
        - Implementations may query network state, consensus logs, or heartbeat status
    """

    def get_cluster_state(self) -> RaftClusterState:
        """Get the current state of all nodes in the cluster.

        Returns:
            A RaftClusterState object containing the state of all nodes
            in the cluster, including their node IDs and leadership status.

        Raises:
            May raise exceptions if cluster state cannot be determined
            (e.g., network unavailable, consensus lost).
        """
        ...


@runtime_checkable
class EventEmitterPort(Protocol):
    """Port interface for emitting failover events.

    Implementations handle event delivery to observers (logging, metrics, callbacks).
    Abstracts the event delivery mechanism from the coordinator that emits events.

    Contract:
        - emit(event) delivers the event to all registered observers
        - emit() is fire-and-forget (no return value, no exceptions propagated)
        - Implementations may buffer, deduplicate, or transform events
        - Thread safety is implementation-defined
    """

    def emit(self, event: FailoverEvent) -> None:
        """Emit a failover event to observers.

        Args:
            event: The FailoverEvent to emit.
        """
        ...


@runtime_checkable
class LoggingPort(Protocol):
    """Port interface for structured logging.

    Implementations handle log message delivery to configured logging backends.
    Abstracts the logging mechanism from use cases that need to emit warnings
    (e.g., when stale reads are detected, split-brain scenarios, etc.).

    Contract:
        - warning(message) logs a warning-level message
        - warning() is fire-and-forget (no return value, no exceptions propagated)
        - Implementations may format, filter, or route messages as needed
        - Thread safety is implementation-defined
    """

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The warning message to log.
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


@runtime_checkable
class ForwardingPort(Protocol):
    """Port interface for forwarding HTTP requests to the primary node.

    Implementations handle the actual HTTP request forwarding when a replica
    receives a write request that needs to go to the primary. This abstracts
    the HTTP client from the forwarding logic.

    Contract:
        - forward_request() sends request to primary and returns response
        - All headers except Host should be preserved
        - X-Forwarded-* headers should be added
        - May raise exceptions for network errors
    """

    def forward_request(
        self,
        primary_url: str,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None = None,
        query_string: str = "",
    ) -> ForwardingResult:
        """Forward an HTTP request to the primary node.

        Args:
            primary_url: Base URL of the primary node (e.g., "http://primary:8080").
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: Request path (e.g., "/api/users").
            headers: Original request headers. Host will be rewritten.
            body: Optional request body bytes.
            query_string: Optional query string (without leading ?).

        Returns:
            ForwardingResult containing status code, headers, and body from primary.

        Raises:
            May raise httpx.RequestError or similar for network failures.
        """
        ...


@runtime_checkable
class TimeProvider(Protocol):
    """Port interface for time operations.

    Implementations provide the current time as a Unix timestamp.
    This abstraction enables deterministic testing through fake implementations
    and supports time-based operations like circuit breaker timeouts and
    retry backoff calculations.

    Contract:
        - get_time_seconds() returns current Unix timestamp as float
        - Returned value must be non-negative
        - Successive calls must return non-decreasing values (monotonic)
    """

    def get_time_seconds(self) -> float:
        """Return current Unix timestamp in seconds.

        Returns:
            Current time as Unix timestamp (seconds since epoch) as float.
            The value includes fractional seconds for sub-second precision.
        """
        ...


class RealTimeProvider:
    """Default implementation: provides real system time.

    Uses time.time() to return the current Unix timestamp.
    Suitable for production use where real time is needed.
    """

    def get_time_seconds(self) -> float:
        """Return current Unix timestamp in seconds.

        Returns:
            Current system time as Unix timestamp (seconds since epoch).
        """
        return time.time()


@runtime_checkable
class BinaryDownloaderPort(Protocol):
    """Port interface for downloading LiteFS binary from remote URL.

    Implementations handle downloading the LiteFS binary from a remote URL
    to a local filesystem path. This abstracts the HTTP download mechanism
    from the binary management use cases.

    Contract:
        - download(url, destination) downloads binary and returns metadata
        - The destination path's parent directory must exist
        - Returns BinaryMetadata with populated download info
        - May raise exceptions for network errors or filesystem errors
    """

    def download(self, url: str, destination: Path) -> BinaryMetadata:
        """Download binary from URL to local filesystem.

        Args:
            url: Remote URL to download the binary from.
            destination: Local filesystem path to save the binary to.
                The parent directory must exist.

        Returns:
            BinaryMetadata containing platform, version, location, and
            optional fields like checksum, size_bytes, and downloaded_at.

        Raises:
            May raise httpx.RequestError or similar for network failures.
            May raise OSError for filesystem errors.
        """
        ...


@runtime_checkable
class PlatformDetectorPort(Protocol):
    """Port interface for detecting current OS and architecture.

    Implementations detect the current platform (operating system and CPU
    architecture) where the code is running. This enables downloading the
    correct LiteFS binary for the current system.

    Contract:
        - detect() returns a Platform value object with os and arch
        - The returned Platform must have valid os ('linux' or 'darwin')
        - The returned Platform must have valid arch ('amd64' or 'arm64')
        - Implementations should return consistent results across multiple calls
    """

    def detect(self) -> Platform:
        """Detect the current platform.

        Returns:
            Platform value object containing:
            - os: Operating system ('linux' or 'darwin')
            - arch: Architecture ('amd64' or 'arm64')
        """
        ...


@runtime_checkable
class BinaryResolverPort(Protocol):
    """Port interface for resolving/finding existing LiteFS binary on filesystem.

    Implementations search for an existing LiteFS binary on the filesystem,
    checking known locations (system paths, user directories, etc.) to find
    where the binary is installed.

    Contract:
        - resolve() returns BinaryLocation if binary found, None if not found
        - The returned BinaryLocation.path must point to an existing file
        - The returned BinaryLocation.is_custom indicates if user-specified
        - Implementations may check multiple locations in priority order
        - Should not download or install the binary - only find existing ones
    """

    def resolve(self) -> BinaryLocation | None:
        """Resolve/find an existing LiteFS binary on the filesystem.

        Returns:
            BinaryLocation if the binary is found, containing:
            - path: Path to the binary location
            - is_custom: True if user-specified, False if default location
            None if the binary is not found on the filesystem.
        """
        ...


@runtime_checkable
class PrimaryMarkerWriterPort(Protocol):
    """Port interface for writing the .primary marker file.

    Implementations write a marker file that LiteFS uses to determine
    which node is the primary (can accept writes) in static lease mode.

    Contract:
        - write_marker(node_id) writes the marker file with the node ID
        - remove_marker() removes the marker file (idempotent)
        - marker_exists() returns True if marker file exists
        - read_marker() returns marker content or None if not exists
    """

    def write_marker(self, node_id: str) -> None:
        """Write the primary marker file.

        Args:
            node_id: The node ID to write to the marker file.

        Raises:
            OSError: If file write fails.
        """
        ...

    def remove_marker(self) -> None:
        """Remove the primary marker file.

        Idempotent: safe to call even if file doesn't exist.

        Raises:
            OSError: If file removal fails (other than FileNotFoundError).
        """
        ...

    def marker_exists(self) -> bool:
        """Check if the primary marker file exists.

        Returns:
            True if .primary file exists, False otherwise.
        """
        ...

    def read_marker(self) -> str | None:
        """Read current marker content.

        Returns:
            The node ID from the marker file, or None if file doesn't exist.
        """
        ...
