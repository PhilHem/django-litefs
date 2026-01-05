"""Unit tests for LiteFSDjangoConfig AppConfig."""

import logging
from unittest.mock import patch, Mock

import pytest

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.usecases.primary_detector import LiteFSNotRunningError
from litefs_django.apps import LiteFSDjangoConfig
from .fakes import (
    FakeMountValidator,
    FakeNodeIDResolver,
    FakePrimaryDetector,
    FakePrimaryInitializer,
    FakePrimaryMarkerWriter,
)


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
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes for injected factories
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="primary-node")
                    fake_initializer = FakePrimaryInitializer(is_primary=True)

                    # Call ready() using test config with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.ready()

                    # Verify behavior: static mode logs primary status
                    assert any(
                        "static mode" in record.message.lower()
                        and "primary" in record.message.lower()
                        for record in caplog.records
                    )

    def test_runtime_leader_election_uses_primary_detector(self, caplog):
        """Test that raft mode uses PrimaryDetector for runtime detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes
                    fake_validator = FakeMountValidator()
                    fake_detector = FakePrimaryDetector(is_primary=False)

                    # Call ready() with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.primary_detector_factory = lambda _: fake_detector
                    config.ready()

                    # Verify behavior: raft mode logs replica status
                    assert any(
                        "raft mode" in record.message.lower()
                        and "replica" in record.message.lower()
                        for record in caplog.records
                    )

    def test_static_mode_logs_primary_status(self, caplog):
        """Test that static mode logs the result of primary detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings for primary node
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

                    # Setup fakes
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="primary-node")
                    fake_initializer = FakePrimaryInitializer(is_primary=True)

                    # Call ready() with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.ready()

                    # Verify logging includes primary status
                    assert any(
                        "primary" in record.message.lower() for record in caplog.records
                    )

    def test_static_mode_handles_missing_node_id_gracefully(self, caplog):
        """Test that static mode handles missing LITEFS_NODE_ID with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes - resolver raises KeyError (missing LITEFS_NODE_ID)
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver()
                    fake_resolver.set_missing_node_id()

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.ready()

                    # Verify warning was logged
                    assert any(
                        "node_id" in record.message.lower()
                        or "litefs_node_id" in record.message.lower()
                        for record in caplog.records
                        if record.levelno >= logging.WARNING
                    )

    def test_static_mode_handles_invalid_node_id(self, caplog):
        """Test that static mode handles invalid LITEFS_NODE_ID with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes - resolver raises ValueError (empty node ID)
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver()
                    fake_resolver.set_invalid_node_id()

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.ready()

                    # Verify warning was logged
                    assert any(
                        "node_id" in record.message.lower()
                        or "invalid" in record.message.lower()
                        for record in caplog.records
                        if record.levelno >= logging.WARNING
                    )

    def test_raft_mode_logs_primary_status(self, caplog):
        """Test that raft mode logs the result of primary detection."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes for injected factories
                    fake_validator = FakeMountValidator()
                    fake_detector = FakePrimaryDetector()
                    fake_detector.set_primary(True)

                    # Call ready() using test config with injected factories
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.primary_detector_factory = lambda _: fake_detector
                    config.ready()

                    # Verify logging includes primary status
                    assert any(
                        "primary" in record.message.lower() for record in caplog.records
                    )

    def test_raft_mode_handles_litefs_not_running(self, caplog):
        """Test that raft mode handles LiteFSNotRunningError gracefully."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fakes - detector raises LiteFSNotRunningError
                    fake_validator = FakeMountValidator()
                    fake_detector = FakePrimaryDetector()
                    fake_detector.set_litefs_not_running()

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.primary_detector_factory = lambda _: fake_detector
                    config.ready()

                    # Verify warning was logged
                    assert any(
                        "litefs" in record.message.lower()
                        and "running" in record.message.lower()
                        for record in caplog.records
                        if record.levelno >= logging.WARNING
                    )

    def test_disabled_litefs_returns_early(self, caplog):
        """Test that disabled LiteFS (ENABLED=False) returns early without processing."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
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
                    assert any(
                        "disabled" in record.message.lower()
                        for record in caplog.records
                    )

    def test_missing_settings_returns_early(self, caplog):
        """Test that missing LITEFS settings returns early with warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup mock - no LITEFS settings (None)
                    mock_getattr.return_value = None

                    # Call ready()
                    config = create_test_config()
                    config.ready()

                    # Verify get_litefs_settings was NOT called
                    mock_get_settings.assert_not_called()

                    # Verify warning was logged
                    assert any(
                        "litefs" in record.message.lower()
                        and "not found" in record.message.lower()
                        for record in caplog.records
                    )

    def test_mount_path_validation_failure_returns_early(self, caplog):
        """Test that mount path validation failure is handled gracefully."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
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

                    # Setup fake - validator raises exception
                    fake_validator = FakeMountValidator()
                    fake_validator.set_error(Exception("Mount path not found"))

                    # Call ready() - should not raise, just warn
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.ready()

                    # Verify warning was logged about validation failure
                    assert any(
                        "validation" in record.message.lower()
                        for record in caplog.records
                        if record.levelno >= logging.WARNING
                    )


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.AppConfig")
class TestPrimaryMarkerWriting:
    """Test .primary marker file writing in static leader election mode."""

    def test_static_mode_writes_marker_when_primary(self, caplog):
        """Test that static mode writes .primary marker when this node is primary."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings for primary node
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

                    # Setup fakes
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="primary-node")
                    fake_initializer = FakePrimaryInitializer(is_primary=True)
                    fake_marker_writer = FakePrimaryMarkerWriter()

                    # Call ready()
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.primary_marker_writer_factory = lambda _: fake_marker_writer
                    config._marker_writer = None
                    config._write_primary_marker = (
                        LiteFSDjangoConfig._write_primary_marker.__get__(config)
                    )
                    config.ready()

                    # Verify marker was written
                    assert fake_marker_writer.marker_exists() is True
                    assert fake_marker_writer.read_marker() == "primary-node"

    def test_static_mode_skips_marker_when_replica(self, caplog):
        """Test that static mode does NOT write .primary marker when this node is replica."""
        with caplog.at_level(logging.INFO):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings for replica node
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

                    # Setup fakes - this node is NOT primary
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="replica-node")
                    fake_initializer = FakePrimaryInitializer(is_primary=False)
                    fake_marker_writer = FakePrimaryMarkerWriter()

                    # Call ready()
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.primary_marker_writer_factory = lambda _: fake_marker_writer
                    config._marker_writer = None
                    config._write_primary_marker = (
                        LiteFSDjangoConfig._write_primary_marker.__get__(config)
                    )
                    config.ready()

                    # Verify marker was NOT written (replica should not write marker)
                    assert fake_marker_writer.marker_exists() is False

    def test_static_mode_handles_marker_write_error_gracefully(self, caplog):
        """Test that marker write errors are handled gracefully (logged, not raised)."""
        with caplog.at_level(logging.ERROR):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings for primary node
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

                    # Setup fakes with write error
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="primary-node")
                    fake_initializer = FakePrimaryInitializer(is_primary=True)
                    fake_marker_writer = FakePrimaryMarkerWriter()
                    fake_marker_writer.set_write_error(
                        OSError("Permission denied: /litefs/.primary")
                    )

                    # Call ready() - should not raise
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.primary_marker_writer_factory = lambda _: fake_marker_writer
                    config._marker_writer = None
                    config._write_primary_marker = (
                        LiteFSDjangoConfig._write_primary_marker.__get__(config)
                    )
                    config.ready()  # Should not raise

                    # Verify error was logged
                    assert any(
                        "failed" in record.message.lower()
                        and ".primary" in record.message
                        for record in caplog.records
                        if record.levelno >= logging.ERROR
                    )

    def test_static_mode_warns_on_existing_different_marker(self, caplog):
        """Test that overwriting a different node's marker logs a warning."""
        with caplog.at_level(logging.WARNING):
            with patch("litefs_django.apps.getattr") as mock_getattr:
                with patch(
                    "litefs_django.apps.get_litefs_settings"
                ) as mock_get_settings:
                    # Setup Django settings
                    mock_getattr.return_value = {
                        "MOUNT_PATH": "/litefs",
                        "DATA_PATH": "/var/lib/litefs",
                        "DATABASE_NAME": "db.sqlite3",
                        "LEADER_ELECTION": "static",
                        "PROXY_ADDR": ":8080",
                        "ENABLED": True,
                        "RETENTION": "1h",
                        "PRIMARY_HOSTNAME": "new-primary",
                    }

                    static_config = StaticLeaderConfig(primary_hostname="new-primary")
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

                    # Setup fakes - marker already exists with different content
                    fake_validator = FakeMountValidator()
                    fake_resolver = FakeNodeIDResolver(node_id="new-primary")
                    fake_initializer = FakePrimaryInitializer(is_primary=True)
                    fake_marker_writer = FakePrimaryMarkerWriter()
                    fake_marker_writer.set_initial_content("old-primary")  # Different!

                    # Call ready()
                    config = create_test_config()
                    config.mount_validator_factory = lambda: fake_validator
                    config.node_id_resolver_factory = lambda: fake_resolver
                    config.primary_initializer_factory = lambda _: fake_initializer
                    config.primary_marker_writer_factory = lambda _: fake_marker_writer
                    config._marker_writer = None
                    config._write_primary_marker = (
                        LiteFSDjangoConfig._write_primary_marker.__get__(config)
                    )
                    config.ready()

                    # Verify warning about overwriting different marker
                    assert any(
                        "overwriting" in record.message.lower()
                        for record in caplog.records
                        if record.levelno >= logging.WARNING
                    )

                    # Marker should still be written with new content
                    assert fake_marker_writer.read_marker() == "new-primary"

    def test_cleanup_removes_marker_on_shutdown(self):
        """Test that _cleanup_primary_marker removes the marker file."""
        fake_marker_writer = FakePrimaryMarkerWriter()
        fake_marker_writer.write_marker("primary-node")
        assert fake_marker_writer.marker_exists() is True

        # Create config and set marker writer
        config = create_test_config()
        config._marker_writer = fake_marker_writer
        config._cleanup_primary_marker = (
            LiteFSDjangoConfig._cleanup_primary_marker.__get__(config)
        )

        # Call cleanup
        config._cleanup_primary_marker()

        # Verify marker was removed
        assert fake_marker_writer.marker_exists() is False

    def test_cleanup_handles_missing_marker_gracefully(self):
        """Test that cleanup is safe when marker doesn't exist."""
        fake_marker_writer = FakePrimaryMarkerWriter()
        # Don't write anything - marker doesn't exist

        config = create_test_config()
        config._marker_writer = fake_marker_writer
        config._cleanup_primary_marker = (
            LiteFSDjangoConfig._cleanup_primary_marker.__get__(config)
        )

        # Call cleanup - should not raise
        config._cleanup_primary_marker()

    def test_cleanup_handles_remove_error_gracefully(self, caplog):
        """Test that cleanup handles remove errors gracefully."""
        with caplog.at_level(logging.WARNING):
            fake_marker_writer = FakePrimaryMarkerWriter()
            fake_marker_writer.write_marker("primary-node")
            fake_marker_writer.set_remove_error(
                OSError("Permission denied: /litefs/.primary")
            )

            config = create_test_config()
            config._marker_writer = fake_marker_writer
            config._cleanup_primary_marker = (
                LiteFSDjangoConfig._cleanup_primary_marker.__get__(config)
            )

            # Call cleanup - should not raise
            config._cleanup_primary_marker()

            # Verify warning was logged
            assert any(
                "failed" in record.message.lower() and ".primary" in record.message
                for record in caplog.records
                if record.levelno >= logging.WARNING
            )

    def test_cleanup_skips_when_no_marker_writer(self):
        """Test that cleanup is safe when _marker_writer is None."""
        config = create_test_config()
        config._marker_writer = None
        config._cleanup_primary_marker = (
            LiteFSDjangoConfig._cleanup_primary_marker.__get__(config)
        )

        # Call cleanup - should not raise
        config._cleanup_primary_marker()
