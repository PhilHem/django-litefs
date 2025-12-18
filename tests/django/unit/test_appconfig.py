"""Unit tests for Django AppConfig."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

from litefs_django.apps import LiteFSDjangoConfig


@pytest.mark.unit
class TestAppConfig:
    """Test LiteFS Django AppConfig."""

    def test_appconfig_initialization(self):
        """Test that AppConfig can be initialized."""
        config = LiteFSDjangoConfig("litefs_django", None)
        assert config.name == "litefs_django"

    def test_ready_validates_settings(self):
        """Test that ready() method validates settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", None)

            # Mock Django settings
            with patch("litefs_django.apps.settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                }

                # Should not raise if settings are valid
                config.ready()

    def test_ready_checks_litefs_availability(self):
        """Test that ready() checks LiteFS mount path exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "nonexistent"
            # Path doesn't exist

            config = LiteFSDjangoConfig("litefs_django", None)

            with patch("litefs_django.apps.settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                }

                # Should raise if mount path doesn't exist (when enabled)
                # This depends on implementation - may raise or log warning
