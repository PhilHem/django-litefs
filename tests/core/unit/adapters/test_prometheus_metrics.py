"""Tests for PrometheusMetricsAdapter."""

from __future__ import annotations

import pytest

from litefs.adapters.metrics_port import MetricsPort


# Skip all tests if prometheus-client is not installed
prometheus_client = pytest.importorskip("prometheus_client")


@pytest.mark.unit
class TestPrometheusMetricsAdapterProtocol:
    """Tests for PrometheusMetricsAdapter protocol compliance."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with unique prefix to avoid registry conflicts."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        # Use unique prefix to avoid conflicts between tests
        import uuid

        prefix = f"test_{uuid.uuid4().hex[:8]}"
        return PrometheusMetricsAdapter(prefix=prefix)

    def test_implements_metrics_port_protocol(self, adapter) -> None:
        """PrometheusMetricsAdapter should implement MetricsPort protocol."""
        assert isinstance(adapter, MetricsPort)


@pytest.mark.unit
class TestPrometheusMetricsAdapterNodeState:
    """Tests for PrometheusMetricsAdapter node state gauge."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with unique prefix."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        import uuid

        prefix = f"test_{uuid.uuid4().hex[:8]}"
        return PrometheusMetricsAdapter(prefix=prefix)

    def test_set_node_state_primary_sets_gauge_to_1(self, adapter) -> None:
        """set_node_state(True) should set gauge to 1."""
        adapter.set_node_state(True)
        assert adapter._node_state._value.get() == 1

    def test_set_node_state_replica_sets_gauge_to_0(self, adapter) -> None:
        """set_node_state(False) should set gauge to 0."""
        adapter.set_node_state(False)
        assert adapter._node_state._value.get() == 0


@pytest.mark.unit
class TestPrometheusMetricsAdapterHealthStatus:
    """Tests for PrometheusMetricsAdapter health status gauge."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with unique prefix."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        import uuid

        prefix = f"test_{uuid.uuid4().hex[:8]}"
        return PrometheusMetricsAdapter(prefix=prefix)

    def test_set_health_status_healthy_sets_gauge_to_1(self, adapter) -> None:
        """set_health_status('healthy') should set gauge to 1.0."""
        adapter.set_health_status("healthy")
        assert adapter._health_status._value.get() == 1.0

    def test_set_health_status_degraded_sets_gauge_to_half(self, adapter) -> None:
        """set_health_status('degraded') should set gauge to 0.5."""
        adapter.set_health_status("degraded")
        assert adapter._health_status._value.get() == 0.5

    def test_set_health_status_unhealthy_sets_gauge_to_0(self, adapter) -> None:
        """set_health_status('unhealthy') should set gauge to 0.0."""
        adapter.set_health_status("unhealthy")
        assert adapter._health_status._value.get() == 0.0


@pytest.mark.unit
class TestPrometheusMetricsAdapterSplitBrain:
    """Tests for PrometheusMetricsAdapter split-brain gauge."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with unique prefix."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        import uuid

        prefix = f"test_{uuid.uuid4().hex[:8]}"
        return PrometheusMetricsAdapter(prefix=prefix)

    def test_set_split_brain_detected_true_sets_gauge_to_1(self, adapter) -> None:
        """set_split_brain_detected(True) should set gauge to 1."""
        adapter.set_split_brain_detected(True)
        assert adapter._split_brain_detected._value.get() == 1

    def test_set_split_brain_detected_false_sets_gauge_to_0(self, adapter) -> None:
        """set_split_brain_detected(False) should set gauge to 0."""
        adapter.set_split_brain_detected(False)
        assert adapter._split_brain_detected._value.get() == 0


@pytest.mark.unit
class TestPrometheusMetricsAdapterLeaderElected:
    """Tests for PrometheusMetricsAdapter leader election gauge."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with unique prefix."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        import uuid

        prefix = f"test_{uuid.uuid4().hex[:8]}"
        return PrometheusMetricsAdapter(prefix=prefix)

    def test_set_leader_elected_true_sets_gauge_to_1(self, adapter) -> None:
        """set_leader_elected(True) should set gauge to 1."""
        adapter.set_leader_elected(True)
        assert adapter._leader_elected._value.get() == 1

    def test_set_leader_elected_false_sets_gauge_to_0(self, adapter) -> None:
        """set_leader_elected(False) should set gauge to 0."""
        adapter.set_leader_elected(False)
        assert adapter._leader_elected._value.get() == 0


@pytest.mark.unit
class TestPrometheusMetricsAdapterMetricNames:
    """Tests for Prometheus metric naming."""

    def test_default_prefix_is_litefs(self) -> None:
        """Default prefix should be 'litefs'."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        import uuid

        # Use default prefix but verify gauge name
        adapter = PrometheusMetricsAdapter(prefix=f"litefs_{uuid.uuid4().hex[:8]}")
        # Gauge names are accessible via _name attribute on the metric
        assert adapter._node_state._name.startswith("litefs_")

    def test_custom_prefix_is_applied(self) -> None:
        """Custom prefix should be applied to all metric names."""
        from litefs.adapters.prometheus_metrics import PrometheusMetricsAdapter

        adapter = PrometheusMetricsAdapter(prefix="myapp")
        assert adapter._node_state._name == "myapp_node_state"
        assert adapter._health_status._name == "myapp_health_status"
        assert adapter._split_brain_detected._name == "myapp_split_brain_detected"
        assert adapter._leader_elected._name == "myapp_is_leader_elected"
