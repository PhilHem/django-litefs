"""Health status domain value object."""

from dataclasses import dataclass
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class HealthStatus:
    """Health status value object.

    Represents the health state of a LiteFS node with three possible states:
    - healthy: Node is operating normally
    - degraded: Node is operating but with reduced capability
    - unhealthy: Node is not operational

    This is a domain value object with zero external dependencies.
    Instances are immutable and can be used as dictionary keys or in sets.

    Attributes:
        state: One of "healthy", "unhealthy", or "degraded".
    """

    state: Literal["healthy", "unhealthy", "degraded"]

    def __post_init__(self) -> None:
        """Validate health state after initialization."""
        self._validate_state()

    def _validate_state(self) -> None:
        """Validate that state is one of the allowed values."""
        valid_states = ("healthy", "unhealthy", "degraded")
        if self.state not in valid_states:
            raise LiteFSConfigError(
                f"health state must be one of {valid_states}, got: {self.state!r}"
            )


@dataclass(frozen=True)
class LivenessResult:
    """Liveness probe result value object.

    Represents the result of a liveness probe for a LiteFS node.
    Used by health check endpoints to report node availability.

    This is a domain value object with zero external dependencies.
    Instances are immutable and can be used as dictionary keys or in sets.

    Attributes:
        is_live: True if the node is alive and responsive.
        error: Optional error message if the node is not live.
    """

    is_live: bool
    error: str | None = None


@dataclass(frozen=True)
class ReadinessResult:
    """Readiness probe result value object.

    Represents the result of a readiness probe for a LiteFS node.
    Used by health check endpoints to determine if the node can accept traffic.

    This is a domain value object with zero external dependencies.
    Instances are immutable and can be used as dictionary keys or in sets.

    Attributes:
        is_ready: True if the node is ready to accept traffic.
        can_accept_writes: True if the node can accept write operations.
        health_status: The overall health status of the node.
        split_brain_detected: True if multiple leaders are detected.
        leader_node_ids: Tuple of node IDs claiming leadership.
        error: Optional error message if the node is not ready.
    """

    is_ready: bool
    can_accept_writes: bool
    health_status: HealthStatus
    split_brain_detected: bool
    leader_node_ids: tuple[str, ...]
    error: str | None = None
