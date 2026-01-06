"""Prometheus metrics adapter for LiteFS.

Implements MetricsPort using prometheus-client library.
Gracefully handles missing prometheus-client (raises ImportError at init).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from prometheus_client import Gauge


class PrometheusMetricsAdapter:
    """Prometheus implementation of MetricsPort.

    Creates and manages Prometheus gauges for LiteFS state metrics.
    All gauges use a configurable prefix (default 'litefs_') for namespace clarity.

    This adapter requires prometheus-client to be installed:
        pip install litefs-py[metrics]

    Example:
        >>> adapter = PrometheusMetricsAdapter(prefix="myapp_litefs")
        >>> adapter.set_node_state(True)  # Sets myapp_litefs_node_state to 1
        >>> adapter.set_health_status("healthy")  # Sets gauge to 1.0

    Raises:
        ImportError: If prometheus-client is not installed.
    """

    def __init__(self, prefix: str = "litefs") -> None:
        """Initialize Prometheus gauges.

        Args:
            prefix: Metric name prefix. Defaults to "litefs".
                   All gauge names will be {prefix}_<metric_name>.

        Raises:
            ImportError: If prometheus-client is not installed.
        """
        # Import here to make prometheus-client optional
        from prometheus_client import Gauge

        self._node_state: Gauge = Gauge(
            f"{prefix}_node_state",
            "Current node state: 1=PRIMARY, 0=REPLICA",
        )
        self._health_status: Gauge = Gauge(
            f"{prefix}_health_status",
            "Health status: 1.0=healthy, 0.5=degraded, 0.0=unhealthy",
        )
        self._split_brain_detected: Gauge = Gauge(
            f"{prefix}_split_brain_detected",
            "Split-brain detected: 1=yes, 0=no",
        )
        self._leader_elected: Gauge = Gauge(
            f"{prefix}_is_leader_elected",
            "Leader election status: 1=elected, 0=not elected",
        )

    def set_node_state(self, is_primary: bool) -> None:
        """Set node state gauge.

        Args:
            is_primary: True for PRIMARY (1), False for REPLICA (0).
        """
        self._node_state.set(1 if is_primary else 0)

    def set_health_status(
        self,
        status: Literal["healthy", "degraded", "unhealthy"],
    ) -> None:
        """Set health status gauge.

        Args:
            status: Health status string. Maps to numeric value:
                   - healthy: 1.0
                   - degraded: 0.5
                   - unhealthy: 0.0
        """
        status_values = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unhealthy": 0.0,
        }
        self._health_status.set(status_values.get(status, 0.0))

    def set_split_brain_detected(self, detected: bool) -> None:
        """Set split-brain detection gauge.

        Args:
            detected: True if split-brain detected (1), False otherwise (0).
        """
        self._split_brain_detected.set(1 if detected else 0)

    def set_leader_elected(self, is_elected: bool) -> None:
        """Set leader election gauge.

        Args:
            is_elected: True if elected (1), False otherwise (0).
        """
        self._leader_elected.set(1 if is_elected else 0)
