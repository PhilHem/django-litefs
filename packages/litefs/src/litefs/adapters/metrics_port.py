"""Port interface and no-op implementation for metrics collection.

Metrics ports follow fire-and-forget semantics: implementations may
buffer, sample, or drop metrics as needed. No exceptions should propagate.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable


@runtime_checkable
class MetricsPort(Protocol):
    """Port interface for metrics collection.

    Implementations handle metrics recording to various backends
    (Prometheus, StatsD, etc.). Abstracts the metrics mechanism from
    use cases that need to emit metrics.

    Contract:
        - All methods are fire-and-forget (no return value, no exceptions)
        - set_* methods update gauges to specific values
        - Thread safety is implementation-defined
        - Implementations may no-op if metrics are disabled
    """

    def set_node_state(self, is_primary: bool) -> None:
        """Set the node state gauge.

        Args:
            is_primary: True if node is PRIMARY (sets gauge to 1),
                       False if REPLICA (sets gauge to 0).
        """
        ...

    def set_health_status(
        self,
        status: Literal["healthy", "degraded", "unhealthy"],
    ) -> None:
        """Set the health status gauge.

        Args:
            status: Health status. Maps to:
                   - healthy: 1.0
                   - degraded: 0.5
                   - unhealthy: 0.0
        """
        ...

    def set_split_brain_detected(self, detected: bool) -> None:
        """Set the split-brain detection gauge.

        Args:
            detected: True if split-brain detected (sets gauge to 1),
                     False otherwise (sets gauge to 0).
        """
        ...

    def set_leader_elected(self, is_elected: bool) -> None:
        """Set the leader election gauge.

        Args:
            is_elected: True if leader elected (sets gauge to 1),
                       False otherwise (sets gauge to 0).
        """
        ...


class NoOpMetricsAdapter:
    """No-operation metrics adapter for when metrics are disabled.

    All methods are no-ops. This allows use cases to unconditionally
    call metrics methods without checking if metrics are enabled.

    Example:
        >>> adapter = NoOpMetricsAdapter()
        >>> adapter.set_node_state(True)  # Does nothing
        >>> adapter.set_health_status("healthy")  # Does nothing
    """

    def set_node_state(self, is_primary: bool) -> None:
        """No-op."""
        pass

    def set_health_status(
        self,
        status: Literal["healthy", "degraded", "unhealthy"],
    ) -> None:
        """No-op."""
        pass

    def set_split_brain_detected(self, detected: bool) -> None:
        """No-op."""
        pass

    def set_leader_elected(self, is_elected: bool) -> None:
        """No-op."""
        pass
