"""Pytest configuration for LiteFS core unit tests."""

from typing import Any


def pytest_configure(config: Any) -> None:
    """Register custom markers for unit tests."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "concurrency: Concurrency tests with threading")
    config.addinivalue_line(
        "markers", "property: Property-based tests using Hypothesis"
    )
    config.addinivalue_line(
        "markers", "no_parallel: Tests that cannot run in parallel with pytest-xdist"
    )
