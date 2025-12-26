"""Unit tests for LiteFSDjangoConfig AppConfig."""

import logging
from unittest.mock import patch, MagicMock, Mock

import pytest

from litefs.adapters.ports import EnvironmentNodeIDResolver
from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs.usecases.primary_initializer import PrimaryInitializer
from litefs_django.apps import LiteFSDjangoConfig


def create_test_config():
    """Factory function to create a test AppConfig instance with necessary attributes."""
    config = Mock(spec=LiteFSDjangoConfig)
    config.ready = LiteFSDjangoConfig.ready.__get__(config)
    config.name = "litefs_django"
    return config


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestLiteFSDjangoConfigReady:
    """Test LiteFSDjangoConfig.ready() method for primary initialization."""

    def test_static_leader_election_uses_primary_initializer(self, caplog):
        """Test that static mode uses PrimaryInitializer for primary detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "static",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "PRIMARY_HOSTNAME": "primary-node",
                    }

                    # Create settings object with static config
                    static_config = StaticLeaderConfig(primary_hostname="primary-node")
                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="static",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        static_leader_config=static_config,
                    )
                    mock_get_settings.return_value = settings

                    # Setup mocks for injected factories
                    mock_validator = MagicMock()
                    mock_resolver = MagicMock()
                    mock_resolver.resolve_node_id.return_value = "primary-node"
                    mock_initializer = MagicMock()
                    mock_initializer.is_primary.return_value = True

                    # Call ready() using test config with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.node_id_resolver_factory = MagicMock(return_value=mock_resolver)
                    config.primary_initializer_factory = MagicMock(return_value=mock_initializer)
                    config.ready()

                    # Verify factories were called
                    config.node_id_resolver_factory.assert_called_once()
                    config.primary_initializer_factory.assert_called_once()
                    mock_initializer.is_primary.assert_called_once_with("primary-node")
                    mock_resolver.resolve_node_id.assert_called_once()

    def test_runtime_leader_election_uses_primary_detector(self, caplog):
        """Test that raft mode uses PrimaryDetector for runtime detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "raft",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "RAFT_SELF_ADDR": "localhost:4321",
                        "RAFT_PEERS": ["node1:4321", "node2:4321"],
                    }

                    # Create settings object for raft mode
                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="raft",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        raft_self_addr="localhost:4321",
                        raft_peers=["node1:4321", "node2:4321"],
                        static_leader_config=None,
                    )
                    mock_get_settings.return_value = settings

                    # Setup validator and detector mocks
                    mock_validator = MagicMock()
                    mock_detector = MagicMock()
                    mock_detector.is_primary.return_value = False

                    # Call ready() with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.primary_detector_factory = MagicMock(return_value=mock_detector)
                    config.ready()

                    # Verify detector factory was called
                    config.primary_detector_factory.assert_called_once_with("/litefs")
                    mock_detector.is_primary.assert_called_once()

    def test_static_mode_logs_primary_status(self, caplog):
        """Test that static mode logs the result of primary detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    with patch("litefs_django.apps.MountValidator") as mock_validator_class:
                        with patch("litefs_django.apps.PrimaryInitializer") as mock_initializer_class:
                            with patch("litefs_django.apps.EnvironmentNodeIDResolver") as mock_resolver_class:
                                # Setup mocks for primary node
                                mock_getattr.return_value = {
                                    "MOUNT_PATH": "/litefs",
                                    "DATA_PATH": "/var/lib/litefs",
                                    "DATABASE_NAME": "db.sqlite3",
                                    "LEADER_ELECTION": "static",
                                    "PROXY_ADDR": ":8080",
                                    "ENABLED": True,
                                    "RETENTION": "1h",
                                    "PRIMARY_HOSTNAME": "primary-node",
                                }

                                static_config = StaticLeaderConfig(primary_hostname="primary-node")
                                settings = LiteFSSettings(
                                    mount_path="/litefs",
                                    data_path="/var/lib/litefs",
                                    database_name="db.sqlite3",
                                    leader_election="static",
                                    proxy_addr=":8080",
                                    enabled=True,
                                    retention="1h",
                                    static_leader_config=static_config,
                                )
                                mock_get_settings.return_value = settings

                                mock_validator = MagicMock()
                                mock_validator_class.return_value = mock_validator

                                mock_resolver = MagicMock()
                                mock_resolver.resolve_node_id.return_value = "primary-node"
                                mock_resolver_class.return_value = mock_resolver

                                mock_initializer = MagicMock()
                                mock_initializer.is_primary.return_value = True
                                mock_initializer_class.return_value = mock_initializer

                                # Call ready()
                                config = create_test_config()
                                config.ready()

                                # Verify logging includes primary status
                                assert any("primary" in record.message.lower() for record in caplog.records)

    def test_static_mode_handles_missing_node_id_gracefully(self, caplog):
        """Test that static mode handles missing LITEFS_NODE_ID with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "static",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "PRIMARY_HOSTNAME": "primary-node",
                    }

                    static_config = StaticLeaderConfig(primary_hostname="primary-node")
                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="static",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        static_leader_config=static_config,
                    )
                    mock_get_settings.return_value = settings

                    # Make resolver raise KeyError (missing LITEFS_NODE_ID)
                    mock_validator = MagicMock()
                    mock_resolver = MagicMock()
                    mock_resolver.resolve_node_id.side_effect = KeyError("LITEFS_NODE_ID")

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.node_id_resolver_factory = MagicMock(return_value=mock_resolver)
                    config.ready()

                    # Verify warning was logged
                    assert any("node_id" in record.message.lower() or "litefs_node_id" in record.message.lower()
                              for record in caplog.records if record.levelno >= logging.WARNING)

    def test_static_mode_handles_invalid_node_id(self, caplog):
        """Test that static mode handles invalid LITEFS_NODE_ID with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "static",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "PRIMARY_HOSTNAME": "primary-node",
                    }

                    static_config = StaticLeaderConfig(primary_hostname="primary-node")
                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="static",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        static_leader_config=static_config,
                    )
                    mock_get_settings.return_value = settings

                    # Make resolver raise ValueError (empty node ID)
                    mock_validator = MagicMock()
                    mock_resolver = MagicMock()
                    mock_resolver.resolve_node_id.side_effect = ValueError("node ID cannot be empty")

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.node_id_resolver_factory = MagicMock(return_value=mock_resolver)
                    config.ready()

                    # Verify warning was logged
                    assert any("node_id" in record.message.lower() or "invalid" in record.message.lower()
                              for record in caplog.records if record.levelno >= logging.WARNING)

    def test_raft_mode_logs_primary_status(self, caplog):
        """Test that raft mode logs the result of primary detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    with patch("litefs_django.apps.MountValidator") as mock_validator_class:
                        with patch("litefs_django.apps.PrimaryDetector") as mock_detector_class:
                            # Setup mocks
                            mock_getattr.return_value = {
                                "MOUNT_PATH": "/litefs",
                                "DATA_PATH": "/var/lib/litefs",
                                "DATABASE_NAME": "db.sqlite3",
                                "LEADER_ELECTION": "raft",
                                "PROXY_ADDR": ":8080",
                                "ENABLED": True,
                                "RETENTION": "1h",
                                "RAFT_SELF_ADDR": "localhost:4321",
                                "RAFT_PEERS": ["node1:4321"],
                            }

                            settings = LiteFSSettings(
                                mount_path="/litefs",
                                data_path="/var/lib/litefs",
                                database_name="db.sqlite3",
                                leader_election="raft",
                                proxy_addr=":8080",
                                enabled=True,
                                retention="1h",
                                raft_self_addr="localhost:4321",
                                raft_peers=["node1:4321"],
                                static_leader_config=None,
                            )
                            mock_get_settings.return_value = settings

                            mock_validator = MagicMock()
                            mock_validator_class.return_value = mock_validator

                            mock_detector = MagicMock()
                            mock_detector.is_primary.return_value = True
                            mock_detector_class.return_value = mock_detector

                            # Call ready()
                            config = create_test_config()
                            config.ready()

                            # Verify logging includes primary status
                            assert any("primary" in record.message.lower() for record in caplog.records)

    def test_raft_mode_handles_litefs_not_running(self, caplog):
        """Test that raft mode handles LiteFSNotRunningError gracefully."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "raft",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "RAFT_SELF_ADDR": "localhost:4321",
                        "RAFT_PEERS": ["node1:4321"],
                    }

                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="raft",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        raft_self_addr="localhost:4321",
                        raft_peers=["node1:4321"],
                        static_leader_config=None,
                    )
                    mock_get_settings.return_value = settings

                    mock_validator = MagicMock()

                    # Make detector raise LiteFSNotRunningError
                    mock_detector = MagicMock()
                    mock_detector.is_primary.side_effect = LiteFSNotRunningError("LiteFS is not running")

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.primary_detector_factory = MagicMock(return_value=mock_detector)
                    config.ready()

                    # Verify warning was logged
                    assert any("litefs" in record.message.lower() and "running" in record.message.lower()
                              for record in caplog.records if record.levelno >= logging.WARNING)

    def test_disabled_litefs_returns_early(self, caplog):
        """Test that disabled LiteFS (ENABLED=False) returns early without processing."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mock - ENABLED=False
                    mock_getattr.return_value = {
                        "ENABLED": False,
                    }

                    # Call ready()
                    config = create_test_config()
                    config.ready()

                    # Verify get_litefs_settings was NOT called
                    mock_get_settings.assert_not_called()

                    # Verify logging mentions that LiteFS is disabled
                    assert any("disabled" in record.message.lower() for record in caplog.records)

    def test_missing_settings_returns_early(self, caplog):
        """Test that missing LITEFS settings returns early with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mock - no LITEFS settings (None)
                    mock_getattr.return_value = None

                    # Call ready()
                    config = create_test_config()
                    config.ready()

                    # Verify get_litefs_settings was NOT called
                    mock_get_settings.assert_not_called()

                    # Verify warning was logged
                    assert any("litefs" in record.message.lower() and "not found" in record.message.lower()
                              for record in caplog.records)

    def test_mount_path_validation_failure_returns_early(self, caplog):
        """Test that mount path validation failure is handled gracefully."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch("litefs_django.apps.get_litefs_settings") as mock_get_settings:
                    # Setup mocks
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "raft",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "RAFT_SELF_ADDR": "localhost:4321",
                        "RAFT_PEERS": ["node1:4321"],
                    }

                    settings = LiteFSSettings(
                        mount_path="/litefs",
                        data_path="/var/lib/litefs",
                        database_name="db.sqlite3",
                        leader_election="raft",
                        proxy_addr=":8080",
                        enabled=True,
                        retention="1h",
                        raft_self_addr="localhost:4321",
                        raft_peers=["node1:4321"],
                        static_leader_config=None,
                    )
                    mock_get_settings.return_value = settings

                    # Make validator raise exception
                    mock_validator = MagicMock()
                    mock_validator.validate.side_effect = Exception("Mount path not found")

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = MagicMock(return_value=mock_validator)
                    config.ready()

                    # Verify warning was logged about validation failure
                    assert any("validation" in record.message.lower()
                              for record in caplog.records if record.levelno >= logging.WARNING)
