"""Fake metrics adapter for testing.

Provides a test double for MetricsPort that records all metric updates
for assertion in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MetricCall:
    """Record of a single metric update.

    Attributes:
        metric_name: Name of the metric that was updated.
        value: Value that was set.
    """

    metric_name: str
    value: float | int | bool | str


class FakeMetricsAdapter:
    """Fake implementation of MetricsPort for testing.

    Records all metric updates for later assertion. Provides methods
    to inspect current state and call history.

    Example:
        >>> fake = FakeMetricsAdapter()
        >>> fake.set_node_state(True)
        >>> fake.current_node_state
        True
        >>> fake.calls
        [MetricCall(metric_name='node_state', value=True)]
    """

    def __init__(self) -> None:
        """Initialize with no recorded state."""
        self._node_state: bool | None = None
        self._health_status: str | None = None
        self._split_brain_detected: bool | None = None
        self._leader_elected: bool | None = None
        self._calls: list[MetricCall] = []

    @property
    def calls(self) -> list[MetricCall]:
        """Return list of all metric update calls.

        Returns a copy to prevent external modification.

        Returns:
            List of MetricCall objects in order of invocation.
        """
        return list(self._calls)

    @property
    def current_node_state(self) -> bool | None:
        """Return last set node state, or None if never set."""
        return self._node_state

    @property
    def current_health_status(self) -> str | None:
        """Return last set health status, or None if never set."""
        return self._health_status

    @property
    def current_split_brain_detected(self) -> bool | None:
        """Return last set split-brain detection state, or None if never set."""
        return self._split_brain_detected

    @property
    def current_leader_elected(self) -> bool | None:
        """Return last set leader election state, or None if never set."""
        return self._leader_elected

    def set_node_state(self, is_primary: bool) -> None:
        """Record node state update.

        Args:
            is_primary: True for PRIMARY, False for REPLICA.
        """
        self._node_state = is_primary
        self._calls.append(MetricCall("node_state", is_primary))

    def set_health_status(
        self,
        status: Literal["healthy", "degraded", "unhealthy"],
    ) -> None:
        """Record health status update.

        Args:
            status: Health status string.
        """
        self._health_status = status
        self._calls.append(MetricCall("health_status", status))

    def set_split_brain_detected(self, detected: bool) -> None:
        """Record split-brain detection update.

        Args:
            detected: True if split-brain detected.
        """
        self._split_brain_detected = detected
        self._calls.append(MetricCall("split_brain_detected", detected))

    def set_leader_elected(self, is_elected: bool) -> None:
        """Record leader election update.

        Args:
            is_elected: True if leader elected.
        """
        self._leader_elected = is_elected
        self._calls.append(MetricCall("leader_elected", is_elected))

    def clear_calls(self) -> None:
        """Clear the recorded calls list.

        Does not reset current_* state values.
        """
        self._calls.clear()

    def reset(self) -> None:
        """Reset all state and calls.

        Clears both the calls list and all current_* state values.
        """
        self._node_state = None
        self._health_status = None
        self._split_brain_detected = None
        self._leader_elected = None
        self._calls.clear()
