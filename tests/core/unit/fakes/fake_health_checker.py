"""Fake health checker for testing."""

from __future__ import annotations

from litefs.domain.health import HealthStatus


class FakeHealthChecker:
    """Fake health checker that returns configurable health status.

    Use this instead of mocking HealthChecker in unit tests for:
    - Faster test execution (no dependencies on PrimaryDetectorPort)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (change health status during test)
    - Error injection (simulate health check failures)

    Example:
        checker = FakeHealthChecker()
        checker.set_health_status(HealthStatus(state="degraded"))
        result = checker.check_health()
        assert result.state == "degraded"
    """

    def __init__(self) -> None:
        """Initialize with healthy status."""
        self._health_status: HealthStatus = HealthStatus(state="healthy")
        self._error: str | None = None

    def check_health(self) -> HealthStatus:
        """Return configured health status or raise configured error.

        Returns:
            The configured HealthStatus.

        Raises:
            RuntimeError: If error was set via set_error().
        """
        if self._error:
            raise RuntimeError(self._error)
        return self._health_status

    def set_health_status(self, status: HealthStatus) -> None:
        """Set health status to return from check_health().

        Args:
            status: New health status to return.
        """
        self._health_status = status

    def set_error(self, error: str | None) -> None:
        """Set error to raise on next check_health() call.

        Args:
            error: Error message to raise as RuntimeError, or None to clear.
        """
        self._error = error
