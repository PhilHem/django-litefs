"""Health checker use case for determining node health."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litefs.domain.health import HealthStatus
from litefs.adapters.ports import PrimaryDetectorPort

if TYPE_CHECKING:
    from litefs.adapters.metrics_port import MetricsPort


class HealthChecker:
    """Determines the health status of a LiteFS node.

    Use case that checks node health by consulting a primary detector port
    and evaluating health flags. Health status follows a priority hierarchy:
    1. unhealthy (highest priority - overrides all)
    2. degraded (medium priority)
    3. healthy (default/healthy state)

    This is a stateless, pure logic component with zero framework dependencies.
    It depends on the PrimaryDetectorPort for checking primary status, but does
    not depend on whether the node is primary or replica.
    """

    def __init__(
        self,
        primary_detector: PrimaryDetectorPort,
        degraded: bool = False,
        unhealthy: bool = False,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize the health checker.

        Args:
            primary_detector: Port implementation for checking if this node is primary.
            degraded: If True, node health is degraded. Defaults to False.
            unhealthy: If True, node is unhealthy. Defaults to False.
                      Takes precedence over degraded flag.
            metrics: Optional port for emitting health metrics.
        """
        self.primary_detector = primary_detector
        self.degraded = degraded
        self.unhealthy = unhealthy
        self._metrics = metrics

    def check_health(self) -> HealthStatus:
        """Check the current health status of this node.

        Evaluates health state based on configured flags using the following
        priority order (highest to lowest):
        1. unhealthy flag -> returns unhealthy status
        2. degraded flag -> returns degraded status
        3. default -> returns healthy status

        The primary detector is consulted but does not affect the health status
        in the current implementation. It may be used for future enhancements
        (e.g., replica lag detection, replication status checks).

        Returns:
            HealthStatus value object representing the current health state.
        """
        # Call detector to ensure it's properly invoked (may be needed for
        # side effects like metrics collection or connection validation)
        self.primary_detector.is_primary()

        # Determine health state based on priority hierarchy
        if self.unhealthy:
            state = "unhealthy"
        elif self.degraded:
            state = "degraded"
        else:
            state = "healthy"

        # Emit health status metric
        if self._metrics is not None:
            self._metrics.set_health_status(state)  # type: ignore

        return HealthStatus(state=state)  # type: ignore
