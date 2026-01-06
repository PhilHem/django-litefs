"""Tests for MetricsPort protocol and NoOpMetricsAdapter."""

from __future__ import annotations

import pytest

from litefs.adapters.metrics_port import MetricsPort, NoOpMetricsAdapter


@pytest.mark.unit
class TestMetricsPortProtocol:
    """Tests for MetricsPort protocol definition."""

    def test_noop_adapter_implements_metrics_port_protocol(self) -> None:
        """NoOpMetricsAdapter should implement MetricsPort protocol."""
        adapter = NoOpMetricsAdapter()
        assert isinstance(adapter, MetricsPort)

    def test_protocol_is_runtime_checkable(self) -> None:
        """MetricsPort should be runtime checkable."""

        # A non-conforming object should not be an instance
        class NotAMetricsAdapter:
            pass

        assert not isinstance(NotAMetricsAdapter(), MetricsPort)


@pytest.mark.unit
class TestNoOpMetricsAdapter:
    """Tests for NoOpMetricsAdapter."""

    def test_set_node_state_primary_is_noop(self) -> None:
        """set_node_state(True) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_node_state(True)
        assert result is None

    def test_set_node_state_replica_is_noop(self) -> None:
        """set_node_state(False) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_node_state(False)
        assert result is None

    def test_set_health_status_healthy_is_noop(self) -> None:
        """set_health_status('healthy') should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_health_status("healthy")
        assert result is None

    def test_set_health_status_degraded_is_noop(self) -> None:
        """set_health_status('degraded') should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_health_status("degraded")
        assert result is None

    def test_set_health_status_unhealthy_is_noop(self) -> None:
        """set_health_status('unhealthy') should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_health_status("unhealthy")
        assert result is None

    def test_set_split_brain_detected_true_is_noop(self) -> None:
        """set_split_brain_detected(True) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_split_brain_detected(True)
        assert result is None

    def test_set_split_brain_detected_false_is_noop(self) -> None:
        """set_split_brain_detected(False) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_split_brain_detected(False)
        assert result is None

    def test_set_leader_elected_true_is_noop(self) -> None:
        """set_leader_elected(True) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_leader_elected(True)
        assert result is None

    def test_set_leader_elected_false_is_noop(self) -> None:
        """set_leader_elected(False) should not raise or return anything."""
        adapter = NoOpMetricsAdapter()
        result = adapter.set_leader_elected(False)
        assert result is None
