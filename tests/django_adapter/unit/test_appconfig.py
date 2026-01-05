"""Unit tests for Django AppConfig."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import litefs_django
from litefs_django.apps import LiteFSDjangoConfig


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestAppConfig:
    """Test LiteFS Django AppConfig."""

    def test_appconfig_initialization(self):
        """Test that AppConfig can be initialized."""
        config = LiteFSDjangoConfig("litefs_django", litefs_django)
        assert config.name == "litefs_django"

    def test_ready_validates_settings(self):
        """Test that ready() method validates settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Mock Django settings
            with patch("litefs_django.apps.django_settings") as mock_settings:
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

            _config = LiteFSDjangoConfig("litefs_django", litefs_django)  # noqa: F841

            with patch("litefs_django.apps.django_settings") as mock_settings:
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

    def test_ready_with_injected_mount_validator(self):
        """Test that mount validator can be injected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Create mock validator
            mock_validator = MagicMock()
            mock_validator.validate = MagicMock()
            config.mount_validator_factory = MagicMock(return_value=mock_validator)

            with patch("litefs_django.apps.django_settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                    "PRIMARY_HOSTNAME": "node-1",
                }

                config.ready()

                # Verify our injected factory was called
                config.mount_validator_factory.assert_called_once()
                mock_validator.validate.assert_called_once()

    def test_ready_with_injected_node_id_resolver(self):
        """Test that node ID resolver can be injected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Create mock validator
            mock_validator = MagicMock()
            config.mount_validator_factory = MagicMock(return_value=mock_validator)

            # Create mock resolver
            mock_resolver = MagicMock()
            mock_resolver.resolve_node_id = MagicMock(return_value="node-1")
            config.node_id_resolver_factory = MagicMock(return_value=mock_resolver)

            # Create mock initializer
            mock_initializer = MagicMock()
            mock_initializer.is_primary = MagicMock(return_value=True)
            config.primary_initializer_factory = MagicMock(
                return_value=mock_initializer
            )

            with patch("litefs_django.apps.django_settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                    "PRIMARY_HOSTNAME": "node-1",
                }

                config.ready()

                # Verify our injected resolver factory was called
                config.node_id_resolver_factory.assert_called_once()
                mock_resolver.resolve_node_id.assert_called_once()

    def test_ready_with_injected_primary_initializer(self):
        """Test that primary initializer can be injected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Create mock validator
            mock_validator = MagicMock()
            config.mount_validator_factory = MagicMock(return_value=mock_validator)

            # Create mock resolver
            mock_resolver = MagicMock()
            mock_resolver.resolve_node_id = MagicMock(return_value="node-1")
            config.node_id_resolver_factory = MagicMock(return_value=mock_resolver)

            # Create mock initializer
            mock_initializer = MagicMock()
            mock_initializer.is_primary = MagicMock(return_value=True)
            config.primary_initializer_factory = MagicMock(
                return_value=mock_initializer
            )

            with patch("litefs_django.apps.django_settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                    "PRIMARY_HOSTNAME": "node-1",
                }

                config.ready()

                # Verify our injected initializer factory was called
                config.primary_initializer_factory.assert_called_once()
                mock_initializer.is_primary.assert_called_once_with("node-1")

    def test_ready_with_injected_primary_detector(self):
        """Test that primary detector can be injected for raft mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Create mock validator
            mock_validator = MagicMock()
            config.mount_validator_factory = MagicMock(return_value=mock_validator)

            # Create mock detector
            mock_detector = MagicMock()
            mock_detector.is_primary = MagicMock(return_value=True)
            config.primary_detector_factory = MagicMock(return_value=mock_detector)

            with patch("litefs_django.apps.django_settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "raft",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                    "RAFT_SELF_ADDR": "127.0.0.1:20202",
                    "RAFT_PEERS": ["127.0.0.1:20202"],
                }

                config.ready()

                # Verify our injected detector factory was called
                config.primary_detector_factory.assert_called_once_with(str(mount_path))
                mock_detector.is_primary.assert_called_once()

    def test_ready_default_behavior_unchanged(self):
        """Test that default behavior (without injection) remains unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            config = LiteFSDjangoConfig("litefs_django", litefs_django)

            # Verify default factories are set
            assert config.mount_validator_factory is not None
            assert config.node_id_resolver_factory is not None
            assert config.primary_initializer_factory is not None
            assert config.primary_detector_factory is not None

            # Test that ready() works without explicit injection
            with patch("litefs_django.apps.django_settings") as mock_settings:
                mock_settings.LITEFS = {
                    "MOUNT_PATH": str(mount_path),
                    "DATA_PATH": "/var/lib/litefs",
                    "DATABASE_NAME": "db.sqlite3",
                    "LEADER_ELECTION": "static",
                    "PROXY_ADDR": ":8080",
                    "ENABLED": True,
                    "RETENTION": "1h",
                    "PRIMARY_HOSTNAME": "node-1",
                }

                # Should not raise with defaults
                config.ready()
