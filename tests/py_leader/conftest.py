"""pytest configuration for py_leader tests."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "tier(level): Test tier level (1=unit, 2=concurrency, 3=integration)"
    )
    config.addinivalue_line(
        "markers", "tra(namespace): Test Responsibility Architecture namespace"
    )
