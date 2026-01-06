"""Tests for HealthChecker metrics integration."""

from __future__ import annotations

import pytest

from litefs.usecases.health_checker import HealthChecker
from litefs.adapters.fakes.fake_metrics import FakeMetricsAdapter


class FakePrimaryDetector:
    """Minimal fake for PrimaryDetectorPort."""

    def __init__(self, is_primary: bool = True) -> None:
        self._is_primary = is_primary

    def is_primary(self) -> bool:
        return self._is_primary


@pytest.mark.unit
class TestHealthCheckerMetricsIntegration:
    """Tests for HealthChecker metrics emission."""

    def test_emits_healthy_metric_when_healthy(self) -> None:
        """Should emit 'healthy' metric when node is healthy."""
        metrics = FakeMetricsAdapter()
        checker = HealthChecker(
            primary_detector=FakePrimaryDetector(),
            metrics=metrics,
        )

        checker.check_health()

        assert metrics.current_health_status == "healthy"

    def test_emits_degraded_metric_when_degraded(self) -> None:
        """Should emit 'degraded' metric when node is degraded."""
        metrics = FakeMetricsAdapter()
        checker = HealthChecker(
            primary_detector=FakePrimaryDetector(),
            degraded=True,
            metrics=metrics,
        )

        checker.check_health()

        assert metrics.current_health_status == "degraded"

    def test_emits_unhealthy_metric_when_unhealthy(self) -> None:
        """Should emit 'unhealthy' metric when node is unhealthy."""
        metrics = FakeMetricsAdapter()
        checker = HealthChecker(
            primary_detector=FakePrimaryDetector(),
            unhealthy=True,
            metrics=metrics,
        )

        checker.check_health()

        assert metrics.current_health_status == "unhealthy"

    def test_works_without_metrics(self) -> None:
        """Should work correctly when metrics not provided."""
        checker = HealthChecker(
            primary_detector=FakePrimaryDetector(),
        )

        # Should not raise
        result = checker.check_health()
        assert result.state == "healthy"

    def test_metrics_updated_on_each_check(self) -> None:
        """Metrics should be updated on each check_health call."""
        metrics = FakeMetricsAdapter()
        checker = HealthChecker(
            primary_detector=FakePrimaryDetector(),
            metrics=metrics,
        )

        checker.check_health()
        assert len(metrics.calls) == 1

        checker.check_health()
        assert len(metrics.calls) == 2
