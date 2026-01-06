"""Fake adapters for FastAPI adapter unit testing.

These in-memory fakes replace real implementations that require I/O
(filesystem, network) for fast, isolated unit tests.

Note: These fakes are framework-agnostic and mirror the Django adapter fakes.
Consider extracting to a shared test utilities location in the future.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.primary_detector import LiteFSNotRunningError

if TYPE_CHECKING:
    from litefs.domain.health import HealthStatus
    from litefs.usecases.failover_coordinator import NodeState
    from litefs.usecases.split_brain_detector import SplitBrainStatus


class FakePrimaryDetector:
    """In-memory fake for PrimaryDetector - no filesystem access.

    Use this instead of mocking PrimaryDetector in unit tests for:
    - Faster test execution (no filesystem I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle primary/replica during test)
    - Error injection (simulate LiteFS failures)

    Implements PrimaryDetectorPort protocol for type safety.
    """

    def __init__(
        self, mount_path: str | None = None, *, is_primary: bool = True
    ) -> None:
        """Initialize with desired state.

        Args:
            mount_path: Ignored. Accepted for signature compatibility.
            is_primary: Initial primary state (default True).
        """
        self._mount_path = mount_path
        self._is_primary = is_primary
        self._error: Exception | None = None

    def is_primary(self) -> bool:
        """Return configured state or raise configured error."""
        if self._error:
            raise self._error
        return self._is_primary

    def set_primary(self, is_primary: bool) -> None:
        """Set primary state for testing."""
        self._is_primary = is_primary

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next is_primary() call."""
        self._error = error

    def set_litefs_not_running(self) -> None:
        """Simulate LiteFS not running on the node."""
        self._error = LiteFSNotRunningError("LiteFS is not running on this node")


class FakeSplitBrainDetectorPort:
    """In-memory fake for SplitBrainDetectorPort - no network access.

    Implements SplitBrainDetectorPort protocol for type safety.
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
        """Return configured cluster state or raise configured error."""
        if self._error:
            raise self._error
        return self._cluster_state

    def set_cluster_state(self, cluster_state: RaftClusterState) -> None:
        """Set cluster state for testing."""
        self._cluster_state = cluster_state

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next get_cluster_state() call."""
        self._error = error


class FakeHealthChecker:
    """In-memory fake for HealthChecker use case - no dependencies.

    Mirrors the HealthChecker.check_health() interface.
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
        """Return configured health status."""
        return self._health_status

    def set_health_status(self, status: str) -> None:
        """Set health status for testing."""
        from litefs.domain.health import HealthStatus

        self._health_status = HealthStatus(state=status)  # type: ignore[arg-type]


class FakeFailoverCoordinator:
    """In-memory fake for FailoverCoordinator use case - no dependencies.

    Mirrors the FailoverCoordinator interface.
    """

    def __init__(self, *, node_state: "NodeState | None" = None) -> None:
        """Initialize with desired node state.

        Args:
            node_state: Initial node state. Defaults to NodeState.PRIMARY.
        """
        from litefs.usecases.failover_coordinator import NodeState

        self._node_state = node_state if node_state is not None else NodeState.PRIMARY
        self._healthy = True

    @property
    def state(self) -> "NodeState":
        """Get the current state of this node."""
        return self._node_state

    def set_node_state(self, state: "NodeState") -> None:
        """Set node state for testing."""
        self._node_state = state

    def coordinate_transition(self) -> None:
        """No-op in fake. State is controlled via set_node_state()."""
        pass

    def is_healthy(self) -> bool:
        """Check if this node is healthy."""
        return self._healthy

    def mark_healthy(self) -> None:
        """Mark this node as healthy."""
        self._healthy = True

    def mark_unhealthy(self) -> None:
        """Mark this node as unhealthy."""
        self._healthy = False


class FakeSplitBrainDetector:
    """In-memory fake for SplitBrainDetector use case - no dependencies.

    Mirrors the SplitBrainDetector.detect_split_brain() interface.
    """

    def __init__(
        self,
        *,
        is_split_brain: bool = False,
        leader_nodes: list[RaftNodeState] | None = None,
    ) -> None:
        """Initialize with desired split-brain state.

        Args:
            is_split_brain: Whether split-brain is detected.
            leader_nodes: List of nodes claiming leadership.
        """
        from litefs.usecases.split_brain_detector import SplitBrainStatus

        if leader_nodes is None:
            leader_nodes = [RaftNodeState(node_id="node1", is_leader=True)]

        self._status = SplitBrainStatus(
            is_split_brain=is_split_brain,
            leader_nodes=tuple(leader_nodes),
        )
        self._error: Exception | None = None

    def detect_split_brain(self) -> "SplitBrainStatus":
        """Return configured split-brain status or raise configured error."""
        if self._error:
            raise self._error
        return self._status

    def set_split_brain(
        self, is_split_brain: bool, leader_nodes: list[RaftNodeState]
    ) -> None:
        """Set split-brain state for testing."""
        from litefs.usecases.split_brain_detector import SplitBrainStatus

        self._status = SplitBrainStatus(
            is_split_brain=is_split_brain,
            leader_nodes=tuple(leader_nodes),
        )

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next detect_split_brain() call."""
        self._error = error
