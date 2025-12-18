"""Unit tests for LiteFSSettings domain entity."""

import pytest
from pathlib import Path

from litefs.domain.settings import LiteFSSettings, LiteFSConfigError


@pytest.mark.unit
class TestLiteFSSettings:
    """Test LiteFSSettings domain entity."""

    def test_create_settings_with_valid_values(self):
        """Test creating settings with valid values."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name="db.sqlite3",
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
        )
        assert settings.mount_path == "/litefs"
        assert settings.data_path == "/var/lib/litefs"
        assert settings.database_name == "db.sqlite3"
        assert settings.leader_election == "static"
        assert settings.proxy_addr == ":8080"
        assert settings.enabled is True
        assert settings.retention == "1h"

    def test_reject_path_traversal_in_mount_path(self):
        """Test that path traversal attacks are rejected."""
        with pytest.raises(LiteFSConfigError, match="path traversal"):
            LiteFSSettings(
                mount_path="../../../etc/passwd",
                data_path="/var/lib/litefs",
                database_name="db.sqlite3",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )

    def test_reject_path_traversal_in_data_path(self):
        """Test that path traversal attacks are rejected in data_path."""
        with pytest.raises(LiteFSConfigError, match="path traversal"):
            LiteFSSettings(
                mount_path="/litefs",
                data_path="../../etc/passwd",
                database_name="db.sqlite3",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )

    def test_require_absolute_paths(self):
        """Test that paths must be absolute."""
        with pytest.raises(LiteFSConfigError, match="absolute"):
            LiteFSSettings(
                mount_path="litefs",  # relative path
                data_path="/var/lib/litefs",
                database_name="db.sqlite3",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )

    def test_validate_leader_election_values(self):
        """Test that leader_election only accepts 'static' or 'raft'."""
        with pytest.raises(LiteFSConfigError, match="leader_election"):
            LiteFSSettings(
                mount_path="/litefs",
                data_path="/var/lib/litefs",
                database_name="db.sqlite3",
                leader_election="invalid",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )
