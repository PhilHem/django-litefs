"""ReadinessChecker use case for determining node readiness.

Checks whether a node is ready to accept traffic by composing
health status, failover state, and split-brain detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from litefs.domain.health import HealthStatus, ReadinessResult
from litefs.usecases.failover_coordinator import NodeState

if TYPE_CHECKING:
    from litefs.usecases.split_brain_detector import SplitBrainStatus


class HealthCheckerProtocol(Protocol):
    """Protocol for health checking."""

    def check_health(self) -> HealthStatus:
        """Check current health status."""
        ...


class FailoverCoordinatorProtocol(Protocol):
    """Protocol for failover coordination."""

    @property
    def state(self) -> NodeState:
        """Get current node state."""
        ...


class SplitBrainDetectorProtocol(Protocol):
    """Protocol for split brain detection."""

    def detect_split_brain(self) -> SplitBrainStatus:
        """Detect split brain condition."""
        ...


class ReadinessChecker:
    """Checks whether a node is ready to accept traffic.

    Composes health status, failover state, and split-brain detection
    to determine overall node readiness. A node is considered ready when:
    - Health status is "healthy" (not degraded or unhealthy)
    - No split-brain condition is detected (if detector is provided)

    The result also indicates whether the node can accept writes (is PRIMARY).

    Dependencies:
        - HealthChecker: For checking node health status
        - FailoverCoordinator: For determining PRIMARY/REPLICA state
        - SplitBrainDetector (optional): For detecting split-brain scenarios

    Thread safety:
        Reads from dependent use cases which are responsible for synchronization.
    """

    def __init__(
        self,
        health_checker: HealthCheckerProtocol,
        failover_coordinator: FailoverCoordinatorProtocol,
        split_brain_detector: SplitBrainDetectorProtocol | None = None,
    ) -> None:
        """Initialize the readiness checker.

        Args:
            health_checker: Use case for checking node health.
            failover_coordinator: Use case for determining node state.
            split_brain_detector: Optional use case for detecting split brain.
        """
        self._health_checker = health_checker
        self._failover_coordinator = failover_coordinator
        self._split_brain_detector = split_brain_detector

    def check_readiness(self) -> ReadinessResult:
        """Check if this node is ready to accept traffic.

        Evaluates readiness based on:
        1. Health status from HealthChecker (must be "healthy")
        2. Split brain detection from SplitBrainDetector (must be false if provided)
        3. Write capability from FailoverCoordinator (PRIMARY can write)

        Returns:
            ReadinessResult containing:
            - is_ready: True if node can accept traffic
            - can_accept_writes: True if node is PRIMARY
            - health_status: Current health status
            - split_brain_detected: True if multiple leaders detected
            - leader_node_ids: IDs of nodes claiming leadership
            - error: Error message if not ready
        """
        # Get health status
        health_status = self._health_checker.check_health()

        # Determine write capability
        can_accept_writes = self._failover_coordinator.state == NodeState.PRIMARY

        # Check for split brain if detector is provided
        split_brain_detected = False
        leader_node_ids: tuple[str, ...] = ()

        if self._split_brain_detector is not None:
            split_brain_status = self._split_brain_detector.detect_split_brain()
            split_brain_detected = split_brain_status.is_split_brain
            leader_node_ids = tuple(
                node.node_id for node in split_brain_status.leader_nodes
            )

        # Determine readiness and error message
        error: str | None = None

        if health_status.state != "healthy":
            error = f"Node is {health_status.state}"
        elif split_brain_detected:
            error = f"Split brain detected: multiple leaders {leader_node_ids}"

        is_ready = health_status.state == "healthy" and not split_brain_detected

        return ReadinessResult(
            is_ready=is_ready,
            can_accept_writes=can_accept_writes,
            health_status=health_status,
            split_brain_detected=split_brain_detected,
            leader_node_ids=leader_node_ids,
            error=error,
        )
