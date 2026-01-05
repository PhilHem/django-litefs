"""Fake adapters for unit testing.

These in-memory fakes replace real implementations that require I/O
(filesystem, network, database) for fast, isolated unit tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.primary_detector import LiteFSNotRunningError

if TYPE_CHECKING:
    from litefs.domain.health import HealthStatus
    from litefs.usecases.failover_coordinator import NodeState


class FakePrimaryDetector:
    """In-memory fake for PrimaryDetector - no filesystem access.

    Use this instead of mocking PrimaryDetector in unit tests for:
    - Faster test execution (no filesystem I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle primary/replica during test)
    - Error injection (simulate LiteFS failures)

    Implements PrimaryDetectorPort protocol for type safety.

    Example:
        def test_write_on_replica(fake_primary_detector):
            fake_primary_detector.set_primary(False)
            cursor = LiteFSCursor(conn, fake_primary_detector)
            with pytest.raises(NotPrimaryError):
                cursor.execute("INSERT ...")
    """

    def __init__(
        self, mount_path: str | None = None, *, is_primary: bool = True
    ) -> None:
        """Initialize with desired state.

        Args:
            mount_path: Ignored. Accepted for signature compatibility with
                PrimaryDetector. Allows this fake to be used as a drop-in
                replacement in tests.
            is_primary: Initial primary state (default True).
        """
        # mount_path is ignored - we're an in-memory fake
        self._mount_path = mount_path
        self._is_primary = is_primary
        self._error: Exception | None = None

    def is_primary(self) -> bool:
        """Return configured state or raise configured error.

        Returns:
            True if primary, False if replica.

        Raises:
            Exception: If error was set via set_error().
        """
        if self._error:
            raise self._error
        return self._is_primary

    def set_primary(self, is_primary: bool) -> None:
        """Set primary state for testing.

        Args:
            is_primary: New primary state.
        """
        self._is_primary = is_primary

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next is_primary() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._error = error

    def set_litefs_not_running(self) -> None:
        """Simulate LiteFS not running on the node.

        After calling this method, is_primary() will raise LiteFSNotRunningError.
        This enables testing the scenario 'Given LiteFS is not running on the node'.

        Example:
            def test_litefs_not_running(fake_primary_detector):
                fake_primary_detector.set_litefs_not_running()
                with pytest.raises(LiteFSNotRunningError):
                    fake_primary_detector.is_primary()
        """
        self._error = LiteFSNotRunningError("LiteFS is not running on this node")


class FakeSplitBrainDetector:
    """In-memory fake for SplitBrainDetectorPort - no network access.

    Use this instead of mocking SplitBrainDetectorPort in unit tests for:
    - Faster test execution (no network I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (configure various cluster states during test)
    - Split-brain scenario testing (multiple leaders, no leaders, etc.)

    Implements SplitBrainDetectorPort protocol for type safety.

    Example:
        def test_split_brain_detection(fake_split_brain_detector):
            # Configure split-brain state (two leaders)
            fake_split_brain_detector.set_cluster_state(
                RaftClusterState(nodes=[
                    RaftNodeState(node_id="node1", is_leader=True),
                    RaftNodeState(node_id="node2", is_leader=True),
                ])
            )
            detector = SplitBrainDetector(port=fake_split_brain_detector)
            result = detector.detect_split_brain()
            assert result.is_split_brain is True
    """

    def __init__(
        self,
        cluster_state: RaftClusterState | None = None,
    ) -> None:
        """Initialize with desired cluster state.

        Args:
            cluster_state: Initial cluster state. If None, creates a default
                healthy cluster with a single leader.
        """
        if cluster_state is None:
            # Default: healthy cluster with single leader
            cluster_state = RaftClusterState(
                nodes=[
                    RaftNodeState(node_id="node1", is_leader=True),
                    RaftNodeState(node_id="node2", is_leader=False),
                    RaftNodeState(node_id="node3", is_leader=False),
                ]
            )
        self._cluster_state = cluster_state
        self._error: Exception | None = None

    def get_cluster_state(self) -> RaftClusterState:
        """Return configured cluster state or raise configured error.

        Returns:
            The configured RaftClusterState.

        Raises:
            Exception: If error was set via set_error().
        """
        if self._error:
            raise self._error
        return self._cluster_state

    def set_cluster_state(self, cluster_state: RaftClusterState) -> None:
        """Set cluster state for testing.

        Args:
            cluster_state: New cluster state to return from get_cluster_state().
        """
        self._cluster_state = cluster_state

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next get_cluster_state() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._error = error


class FakeHealthChecker:
    """In-memory fake for HealthChecker use case - no dependencies.

    Use this instead of mocking HealthChecker in unit tests for:
    - Faster test execution (no dependency chain)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle health status during test)

    Mirrors the HealthChecker.check_health() interface.

    Example:
        def test_unhealthy_node(fake_health_checker):
            fake_health_checker.set_health_status("unhealthy")
            status = fake_health_checker.check_health()
            assert status.state == "unhealthy"
    """

    def __init__(self, *, health_status: str = "healthy") -> None:
        """Initialize with desired health state.

        Args:
            health_status: Initial health status. One of "healthy", "degraded",
                or "unhealthy". Defaults to "healthy".
        """
        from litefs.domain.health import HealthStatus

        self._health_status = HealthStatus(state=health_status)  # type: ignore[arg-type]

    def check_health(self) -> "HealthStatus":
        """Return configured health status.

        Returns:
            HealthStatus value object with configured state.
        """
        return self._health_status

    def set_health_status(self, status: str) -> None:
        """Set health status for testing.

        Args:
            status: New health status. One of "healthy", "degraded", or "unhealthy".
        """
        from litefs.domain.health import HealthStatus

        self._health_status = HealthStatus(state=status)  # type: ignore[arg-type]


class FakeFailoverCoordinator:
    """In-memory fake for FailoverCoordinator use case - no dependencies.

    Use this instead of mocking FailoverCoordinator in unit tests for:
    - Faster test execution (no dependency chain)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle node state during test)

    Mirrors the FailoverCoordinator interface.

    Example:
        def test_replica_state(fake_failover_coordinator):
            fake_failover_coordinator.set_node_state(NodeState.REPLICA)
            assert fake_failover_coordinator.state == NodeState.REPLICA
    """

    def __init__(self, *, node_state: "NodeState | None" = None) -> None:
        """Initialize with desired node state.

        Args:
            node_state: Initial node state. Defaults to NodeState.PRIMARY.
        """
        from litefs.usecases.failover_coordinator import NodeState

        self._node_state = node_state if node_state is not None else NodeState.PRIMARY
        self._healthy = True
        self._can_become_leader = True
        self._can_maintain_leadership = True

    @property
    def state(self) -> "NodeState":
        """Get the current state of this node.

        Returns:
            NodeState.PRIMARY or NodeState.REPLICA.
        """
        return self._node_state

    def set_node_state(self, state: "NodeState") -> None:
        """Set node state for testing.

        Args:
            state: New node state (NodeState.PRIMARY or NodeState.REPLICA).
        """
        self._node_state = state

    def coordinate_transition(self) -> None:
        """No-op in fake. State is controlled via set_node_state()."""
        pass

    def can_become_leader(self) -> bool:
        """Check if this node can become the leader.

        Returns:
            Configured value (default True).
        """
        return self._can_become_leader and self._healthy

    def set_can_become_leader(self, value: bool) -> None:
        """Set can_become_leader return value for testing.

        Args:
            value: Value to return from can_become_leader().
        """
        self._can_become_leader = value

    def can_maintain_leadership(self) -> bool:
        """Check if this node can maintain leadership.

        Returns:
            Configured value (default True).
        """
        return self._can_maintain_leadership and self._healthy

    def set_can_maintain_leadership(self, value: bool) -> None:
        """Set can_maintain_leadership return value for testing.

        Args:
            value: Value to return from can_maintain_leadership().
        """
        self._can_maintain_leadership = value

    def is_healthy(self) -> bool:
        """Check if this node is healthy.

        Returns:
            True if healthy, False if unhealthy.
        """
        return self._healthy

    def mark_healthy(self) -> None:
        """Mark this node as healthy."""
        self._healthy = True

    def mark_unhealthy(self) -> None:
        """Mark this node as unhealthy."""
        self._healthy = False

    def perform_graceful_handoff(self) -> None:
        """Perform graceful handoff - transitions to REPLICA."""
        from litefs.usecases.failover_coordinator import NodeState

        self._node_state = NodeState.REPLICA

    def demote_for_health(self) -> None:
        """Demote for health - transitions to REPLICA."""
        from litefs.usecases.failover_coordinator import NodeState

        self._node_state = NodeState.REPLICA

    def demote_for_quorum_loss(self) -> None:
        """Demote for quorum loss - transitions to REPLICA."""
        from litefs.usecases.failover_coordinator import NodeState

        self._node_state = NodeState.REPLICA


class FakePrimaryMarkerWriter:
    """In-memory fake for PrimaryMarkerWriter - no filesystem access.

    Use this instead of mocking PrimaryMarkerWriter in unit tests for:
    - Faster test execution (no filesystem I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (track marker content during test)
    - Error injection (simulate filesystem failures)

    Implements PrimaryMarkerWriterPort protocol for type safety.

    Example:
        def test_static_mode_writes_marker(fake_marker_writer):
            fake_marker_writer.write_marker("node1")
            assert fake_marker_writer.read_marker() == "node1"
            assert fake_marker_writer.marker_exists() is True
    """

    def __init__(self, mount_path: str | None = None) -> None:
        """Initialize with empty marker.

        Args:
            mount_path: Ignored. Accepted for signature compatibility with
                PrimaryMarkerWriter. Allows this fake to be used as a drop-in
                replacement in tests.
        """
        # mount_path is ignored - we're an in-memory fake
        self._mount_path = mount_path
        self._content: str | None = None
        self._write_error: Exception | None = None
        self._remove_error: Exception | None = None

    def write_marker(self, node_id: str) -> None:
        """Write the marker (in-memory).

        Args:
            node_id: The node ID to store.

        Raises:
            Exception: If write error was set via set_write_error().
        """
        if self._write_error:
            raise self._write_error
        self._content = node_id

    def remove_marker(self) -> None:
        """Remove the marker (in-memory).

        Idempotent: safe to call even if marker not set.

        Raises:
            Exception: If remove error was set via set_remove_error().
        """
        if self._remove_error:
            raise self._remove_error
        self._content = None

    def marker_exists(self) -> bool:
        """Check if marker has content.

        Returns:
            True if marker content is set, False otherwise.
        """
        return self._content is not None

    def read_marker(self) -> str | None:
        """Read marker content.

        Returns:
            The stored node ID, or None if not set.
        """
        return self._content

    def set_write_error(self, error: Exception | None) -> None:
        """Set error to raise on next write_marker() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._write_error = error

    def set_remove_error(self, error: Exception | None) -> None:
        """Set error to raise on next remove_marker() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._remove_error = error

    def set_initial_content(self, content: str | None) -> None:
        """Set initial marker content for testing scenarios.

        Useful for testing overwrite warning scenarios where
        a different node's marker already exists.

        Args:
            content: Initial content, or None to clear.
        """
        self._content = content


class FakeMountValidator:
    """In-memory fake for MountValidator - no filesystem access.

    Use this instead of mocking MountValidator in unit tests for:
    - Faster test execution (no filesystem I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Error injection (simulate mount validation failures)

    Example:
        def test_mount_validation_failure(fake_mount_validator):
            fake_mount_validator.set_error(Exception("Mount not found"))
            # Test code that calls validator.validate()
    """

    def __init__(self) -> None:
        """Initialize with no errors (validation passes)."""
        self._error: Exception | None = None

    def validate(self, path: "Path") -> None:
        """Validate mount path or raise configured error.

        Args:
            path: Mount path to validate (ignored in fake).

        Raises:
            Exception: If error was set via set_error().
        """
        if self._error:
            raise self._error

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next validate() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._error = error


class FakeNodeIDResolver:
    """In-memory fake for NodeIDResolver - no environment access.

    Use this instead of mocking NodeIDResolver in unit tests for:
    - Faster test execution (no environment variable access)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (configure node ID during test)
    - Error injection (simulate missing LITEFS_NODE_ID)

    Example:
        def test_primary_detection(fake_node_id_resolver):
            fake_node_id_resolver.set_node_id("primary-node")
            resolver = fake_node_id_resolver
            assert resolver.resolve_node_id() == "primary-node"
    """

    def __init__(self, node_id: str = "test-node") -> None:
        """Initialize with default node ID.

        Args:
            node_id: Initial node ID to return.
        """
        self._node_id = node_id
        self._error: Exception | None = None

    def resolve_node_id(self) -> str:
        """Return configured node ID or raise configured error.

        Returns:
            The configured node ID.

        Raises:
            Exception: If error was set via set_error().
        """
        if self._error:
            raise self._error
        return self._node_id

    def set_node_id(self, node_id: str) -> None:
        """Set node ID for testing.

        Args:
            node_id: New node ID to return.
        """
        self._node_id = node_id

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next resolve_node_id() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._error = error

    def set_missing_node_id(self) -> None:
        """Simulate missing LITEFS_NODE_ID environment variable.

        After calling this, resolve_node_id() will raise KeyError.
        """
        self._error = KeyError("LITEFS_NODE_ID")

    def set_invalid_node_id(self) -> None:
        """Simulate invalid (empty) LITEFS_NODE_ID.

        After calling this, resolve_node_id() will raise ValueError.
        """
        self._error = ValueError("node ID cannot be empty")


class FakePrimaryInitializer:
    """In-memory fake for PrimaryInitializer - no dependencies.

    Use this instead of mocking PrimaryInitializer in unit tests for:
    - Faster test execution (no dependency chain)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle primary status during test)

    Example:
        def test_static_mode_primary(fake_primary_initializer):
            fake_primary_initializer.set_primary(True)
            assert fake_primary_initializer.is_primary("any-node") is True
    """

    def __init__(
        self, static_leader_config: "Any" = None, *, is_primary: bool = True
    ) -> None:
        """Initialize with desired primary state.

        Args:
            static_leader_config: Ignored. Accepted for signature compatibility
                with PrimaryInitializer.
            is_primary: Initial primary state (default True).
        """
        # static_leader_config is ignored - we're an in-memory fake
        self._is_primary = is_primary

    def is_primary(self, node_id: str) -> bool:
        """Return configured primary state.

        Args:
            node_id: Node ID to check (ignored in fake).

        Returns:
            True if configured as primary, False otherwise.
        """
        return self._is_primary

    def set_primary(self, is_primary: bool) -> None:
        """Set primary state for testing.

        Args:
            is_primary: New primary state.
        """
        self._is_primary = is_primary
