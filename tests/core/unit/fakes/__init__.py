"""Fake adapters for testing."""

from .fake_failover_coordinator import FakeFailoverCoordinator
from .fake_health_checker import FakeHealthChecker
from .fake_logging_adapter import FakeLoggingAdapter

__all__ = ["FakeFailoverCoordinator", "FakeHealthChecker", "FakeLoggingAdapter"]
