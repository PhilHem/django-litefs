"""Tests for LiteFSSettings metrics configuration."""

from __future__ import annotations

import pytest

from litefs.domain.settings import LiteFSSettings


def create_minimal_settings(**kwargs) -> LiteFSSettings:
    """Create a minimal valid LiteFSSettings with optional overrides."""
    defaults = {
        "mount_path": "/mnt/litefs",
        "data_path": "/var/lib/litefs",
        "database_name": "db.sqlite3",
        "leader_election": "static",
        "proxy_addr": ":8080",
        "enabled": True,
        "retention": "24h",
    }
    defaults.update(kwargs)
    return LiteFSSettings(**defaults)


@pytest.mark.unit
class TestLiteFSSettingsMetrics:
    """Tests for metrics-related settings on LiteFSSettings."""

    def test_metrics_enabled_defaults_to_false(self) -> None:
        """metrics_enabled should default to False."""
        settings = create_minimal_settings()
        assert settings.metrics_enabled is False

    def test_metrics_enabled_can_be_set_true(self) -> None:
        """metrics_enabled can be set to True."""
        settings = create_minimal_settings(metrics_enabled=True)
        assert settings.metrics_enabled is True

    def test_metrics_prefix_defaults_to_litefs(self) -> None:
        """metrics_prefix should default to 'litefs'."""
        settings = create_minimal_settings()
        assert settings.metrics_prefix == "litefs"

    def test_metrics_prefix_can_be_customized(self) -> None:
        """metrics_prefix can be set to a custom value."""
        settings = create_minimal_settings(metrics_prefix="myapp_litefs")
        assert settings.metrics_prefix == "myapp_litefs"
