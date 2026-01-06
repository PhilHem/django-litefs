"""Tests for FakeMetricsAdapter."""

from __future__ import annotations

import pytest

from litefs.adapters.metrics_port import MetricsPort
from litefs.adapters.fakes.fake_metrics import FakeMetricsAdapter, MetricCall


@pytest.mark.unit
class TestFakeMetricsAdapterProtocol:
    """Tests for FakeMetricsAdapter protocol compliance."""

    def test_implements_metrics_port_protocol(self) -> None:
        """FakeMetricsAdapter should implement MetricsPort protocol."""
        adapter = FakeMetricsAdapter()
        assert isinstance(adapter, MetricsPort)


@pytest.mark.unit
class TestFakeMetricsAdapterNodeState:
    """Tests for FakeMetricsAdapter node state tracking."""

    def test_set_node_state_primary_records_state(self) -> None:
        """set_node_state(True) should record PRIMARY state."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        assert adapter.current_node_state is True

    def test_set_node_state_replica_records_state(self) -> None:
        """set_node_state(False) should record REPLICA state."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(False)
        assert adapter.current_node_state is False

    def test_set_node_state_records_call(self) -> None:
        """set_node_state should record call in calls list."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        assert len(adapter.calls) == 1
        assert adapter.calls[0] == MetricCall("node_state", True)


@pytest.mark.unit
class TestFakeMetricsAdapterHealthStatus:
    """Tests for FakeMetricsAdapter health status tracking."""

    def test_set_health_status_healthy_records_status(self) -> None:
        """set_health_status('healthy') should record healthy status."""
        adapter = FakeMetricsAdapter()
        adapter.set_health_status("healthy")
        assert adapter.current_health_status == "healthy"

    def test_set_health_status_degraded_records_status(self) -> None:
        """set_health_status('degraded') should record degraded status."""
        adapter = FakeMetricsAdapter()
        adapter.set_health_status("degraded")
        assert adapter.current_health_status == "degraded"

    def test_set_health_status_unhealthy_records_status(self) -> None:
        """set_health_status('unhealthy') should record unhealthy status."""
        adapter = FakeMetricsAdapter()
        adapter.set_health_status("unhealthy")
        assert adapter.current_health_status == "unhealthy"

    def test_set_health_status_records_call(self) -> None:
        """set_health_status should record call in calls list."""
        adapter = FakeMetricsAdapter()
        adapter.set_health_status("degraded")
        assert len(adapter.calls) == 1
        assert adapter.calls[0] == MetricCall("health_status", "degraded")


@pytest.mark.unit
class TestFakeMetricsAdapterSplitBrain:
    """Tests for FakeMetricsAdapter split-brain tracking."""

    def test_set_split_brain_detected_true_records_state(self) -> None:
        """set_split_brain_detected(True) should record detected state."""
        adapter = FakeMetricsAdapter()
        adapter.set_split_brain_detected(True)
        assert adapter.current_split_brain_detected is True

    def test_set_split_brain_detected_false_records_state(self) -> None:
        """set_split_brain_detected(False) should record not detected state."""
        adapter = FakeMetricsAdapter()
        adapter.set_split_brain_detected(False)
        assert adapter.current_split_brain_detected is False

    def test_set_split_brain_detected_records_call(self) -> None:
        """set_split_brain_detected should record call in calls list."""
        adapter = FakeMetricsAdapter()
        adapter.set_split_brain_detected(True)
        assert len(adapter.calls) == 1
        assert adapter.calls[0] == MetricCall("split_brain_detected", True)


@pytest.mark.unit
class TestFakeMetricsAdapterLeaderElected:
    """Tests for FakeMetricsAdapter leader election tracking."""

    def test_set_leader_elected_true_records_state(self) -> None:
        """set_leader_elected(True) should record elected state."""
        adapter = FakeMetricsAdapter()
        adapter.set_leader_elected(True)
        assert adapter.current_leader_elected is True

    def test_set_leader_elected_false_records_state(self) -> None:
        """set_leader_elected(False) should record not elected state."""
        adapter = FakeMetricsAdapter()
        adapter.set_leader_elected(False)
        assert adapter.current_leader_elected is False

    def test_set_leader_elected_records_call(self) -> None:
        """set_leader_elected should record call in calls list."""
        adapter = FakeMetricsAdapter()
        adapter.set_leader_elected(True)
        assert len(adapter.calls) == 1
        assert adapter.calls[0] == MetricCall("leader_elected", True)


@pytest.mark.unit
class TestFakeMetricsAdapterUtilityMethods:
    """Tests for FakeMetricsAdapter utility methods."""

    def test_initial_state_is_none(self) -> None:
        """All current_* properties should be None initially."""
        adapter = FakeMetricsAdapter()
        assert adapter.current_node_state is None
        assert adapter.current_health_status is None
        assert adapter.current_split_brain_detected is None
        assert adapter.current_leader_elected is None

    def test_initial_calls_is_empty(self) -> None:
        """calls should be empty list initially."""
        adapter = FakeMetricsAdapter()
        assert adapter.calls == []

    def test_clear_calls_removes_calls(self) -> None:
        """clear_calls should remove all recorded calls."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        adapter.set_health_status("healthy")
        assert len(adapter.calls) == 2

        adapter.clear_calls()
        assert adapter.calls == []

    def test_clear_calls_preserves_current_state(self) -> None:
        """clear_calls should preserve current_* values."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        adapter.set_health_status("healthy")
        adapter.clear_calls()

        assert adapter.current_node_state is True
        assert adapter.current_health_status == "healthy"

    def test_reset_clears_everything(self) -> None:
        """reset should clear all state and calls."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        adapter.set_health_status("healthy")
        adapter.set_split_brain_detected(True)
        adapter.set_leader_elected(True)

        adapter.reset()

        assert adapter.current_node_state is None
        assert adapter.current_health_status is None
        assert adapter.current_split_brain_detected is None
        assert adapter.current_leader_elected is None
        assert adapter.calls == []

    def test_calls_returns_copy(self) -> None:
        """calls property should return a copy to prevent external modification."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        calls = adapter.calls
        calls.clear()
        assert len(adapter.calls) == 1  # Original unchanged

    def test_multiple_calls_recorded_in_order(self) -> None:
        """Multiple calls should be recorded in order."""
        adapter = FakeMetricsAdapter()
        adapter.set_node_state(True)
        adapter.set_health_status("healthy")
        adapter.set_split_brain_detected(False)
        adapter.set_leader_elected(True)

        assert len(adapter.calls) == 4
        assert adapter.calls[0] == MetricCall("node_state", True)
        assert adapter.calls[1] == MetricCall("health_status", "healthy")
        assert adapter.calls[2] == MetricCall("split_brain_detected", False)
        assert adapter.calls[3] == MetricCall("leader_elected", True)
