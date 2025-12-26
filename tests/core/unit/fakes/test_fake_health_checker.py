"""Tests for FakeHealthChecker."""

import pytest

from litefs.domain.health import HealthStatus
from .fake_health_checker import FakeHealthChecker


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Contract.FakeHealthChecker")
class TestFakeHealthChecker:
    """Tests for FakeHealthChecker fake implementation."""

    def test_default_status_is_healthy(self) -> None:
        """New checker should return healthy status by default."""
        checker = FakeHealthChecker()
        result = checker.check_health()
        assert result.state == "healthy"

    def test_check_health_returns_configured_status(self) -> None:
        """check_health() should return the configured status."""
        checker = FakeHealthChecker()
        checker.set_health_status(HealthStatus(state="degraded"))
        result = checker.check_health()
        assert result.state == "degraded"

    def test_set_health_status_changes_return_value(self) -> None:
        """set_health_status() should change what check_health() returns."""
        checker = FakeHealthChecker()
        checker.set_health_status(HealthStatus(state="unhealthy"))
        result = checker.check_health()
        assert result.state == "unhealthy"

    def test_all_health_states(self) -> None:
        """All valid health states should be supported."""
        checker = FakeHealthChecker()
        for state in ["healthy", "degraded", "unhealthy"]:
            checker.set_health_status(HealthStatus(state=state))  # type: ignore[arg-type]
            result = checker.check_health()
            assert result.state == state

    def test_set_error_causes_exception(self) -> None:
        """set_error() should cause check_health() to raise RuntimeError."""
        checker = FakeHealthChecker()
        checker.set_error("simulated failure")
        with pytest.raises(RuntimeError, match="simulated failure"):
            checker.check_health()

    def test_clear_error(self) -> None:
        """set_error(None) should clear the error."""
        checker = FakeHealthChecker()
        checker.set_error("some error")
        checker.set_error(None)
        result = checker.check_health()
        assert result.state == "healthy"

    def test_error_takes_precedence_over_status(self) -> None:
        """Error should be raised even if status is set."""
        checker = FakeHealthChecker()
        checker.set_health_status(HealthStatus(state="degraded"))
        checker.set_error("error overrides status")
        with pytest.raises(RuntimeError, match="error overrides status"):
            checker.check_health()
