"""Unit tests for Django settings reader."""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import patch

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig, LiteFSConfigError
from litefs_django.settings import get_litefs_settings


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestSettingsReader:
    """Test Django settings reader."""

    def test_convert_django_dict_to_litefs_settings(self):
        """Test basic conversion from Django dict to LiteFSSettings."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
        }
        settings = get_litefs_settings(django_settings)
        assert isinstance(settings, LiteFSSettings)
        assert settings.mount_path == "/litefs"
        assert settings.data_path == "/var/lib/litefs"
        assert settings.database_name == "db.sqlite3"
        assert settings.leader_election == "static"
        assert settings.proxy_addr == ":8080"
        assert settings.enabled is True
        assert settings.retention == "1h"

    def test_case_sensitivity_mapping_upper_to_snake(self):
        """Test that UPPER_CASE Django keys map to snake_case domain fields."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
            "RAFT_SELF_ADDR": "localhost:4321",
            "RAFT_PEERS": ["node1:4321", "node2:4321"],
        }
        settings = get_litefs_settings(django_settings)
        assert settings.raft_self_addr == "localhost:4321"
        assert settings.raft_peers == ["node1:4321", "node2:4321"]

    def test_optional_fields_with_none(self):
        """Test that optional fields can be None."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
            "RAFT_SELF_ADDR": None,
            "RAFT_PEERS": None,
        }
        settings = get_litefs_settings(django_settings)
        assert settings.raft_self_addr is None
        assert settings.raft_peers is None

    def test_optional_fields_missing(self):
        """Test that optional fields can be missing from dict."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
        }
        settings = get_litefs_settings(django_settings)
        assert settings.raft_self_addr is None
        assert settings.raft_peers is None

    def test_validation_delegates_to_domain(self):
        """Test that validation errors from domain are raised."""
        django_settings = {
            "MOUNT_PATH": "../../etc/passwd",  # Invalid path traversal
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
        }
        with pytest.raises(LiteFSConfigError, match="path traversal"):
            get_litefs_settings(django_settings)

    @pytest.mark.tier(3)
    @given(
        mount_path=st.just("/litefs"),
        data_path=st.just("/var/lib/litefs"),
        database_name=st.text(min_size=1, max_size=50),
        leader_election=st.sampled_from(["static", "raft"]),
        proxy_addr=st.text(min_size=1, max_size=50),
        enabled=st.booleans(),
        retention=st.text(min_size=1, max_size=20),
        primary_hostname=st.one_of(st.none(), st.text(
            alphabet=st.characters(
                min_codepoint=33, max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1, max_size=50
        )),
        raft_self_addr=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        raft_peers=st.one_of(
            st.none(),
            st.lists(st.text(min_size=1, max_size=100), max_size=10),
        ),
    )
    def test_round_trip_idempotence(
        self,
        mount_path,
        data_path,
        database_name,
        leader_election,
        proxy_addr,
        enabled,
        retention,
        primary_hostname,
        raft_self_addr,
        raft_peers,
    ):
        """Property-based test: Django dict → LiteFSSettings → Django dict should be idempotent."""
        # Skip if values would fail domain validation
        if ".." in mount_path or ".." in data_path:
            return
        if not mount_path.startswith("/") or not data_path.startswith("/"):
            return

        # For static mode, PRIMARY_HOSTNAME is required
        if leader_election == "static" and primary_hostname is None:
            return

        # For raft mode, raft_self_addr and raft_peers are required
        if leader_election == "raft":
            if raft_self_addr is None or not raft_self_addr.strip():
                return
            if raft_peers is None or len(raft_peers) == 0:
                return

        django_settings = {
            "MOUNT_PATH": mount_path,
            "DATA_PATH": data_path,
            "DATABASE_NAME": database_name,
            "LEADER_ELECTION": leader_election,
            "PROXY_ADDR": proxy_addr,
            "ENABLED": enabled,
            "RETENTION": retention,
        }
        # Only add PRIMARY_HOSTNAME if in static mode
        if leader_election == "static" and primary_hostname is not None:
            django_settings["PRIMARY_HOSTNAME"] = primary_hostname
        if raft_self_addr is not None:
            django_settings["RAFT_SELF_ADDR"] = raft_self_addr
        if raft_peers is not None:
            django_settings["RAFT_PEERS"] = raft_peers

        # Convert to domain
        settings = get_litefs_settings(django_settings)

        # Convert back to Django dict format
        converted_back = {
            "MOUNT_PATH": settings.mount_path,
            "DATA_PATH": settings.data_path,
            "DATABASE_NAME": settings.database_name,
            "LEADER_ELECTION": settings.leader_election,
            "PROXY_ADDR": settings.proxy_addr,
            "ENABLED": settings.enabled,
            "RETENTION": settings.retention,
        }
        # Only include PRIMARY_HOSTNAME in converted_back if it was in the original
        # (not for raft mode, where it shouldn't appear in converted_back even if generated)
        if "PRIMARY_HOSTNAME" in django_settings:
            if settings.static_leader_config is not None:
                converted_back["PRIMARY_HOSTNAME"] = settings.static_leader_config.primary_hostname
        if settings.raft_self_addr is not None:
            converted_back["RAFT_SELF_ADDR"] = settings.raft_self_addr
        if settings.raft_peers is not None:
            converted_back["RAFT_PEERS"] = settings.raft_peers

        # Check idempotence
        assert converted_back["MOUNT_PATH"] == django_settings["MOUNT_PATH"]
        assert converted_back["DATA_PATH"] == django_settings["DATA_PATH"]
        assert converted_back["DATABASE_NAME"] == django_settings["DATABASE_NAME"]
        assert converted_back["LEADER_ELECTION"] == django_settings["LEADER_ELECTION"]
        assert converted_back["PROXY_ADDR"] == django_settings["PROXY_ADDR"]
        assert converted_back["ENABLED"] == django_settings["ENABLED"]
        assert converted_back["RETENTION"] == django_settings["RETENTION"]
        assert converted_back.get("PRIMARY_HOSTNAME") == django_settings.get("PRIMARY_HOSTNAME")
        assert converted_back.get("RAFT_SELF_ADDR") == django_settings.get(
            "RAFT_SELF_ADDR"
        )
        assert converted_back.get("RAFT_PEERS") == django_settings.get("RAFT_PEERS")

    def test_validation_matches_domain_absolute_paths(self):
        """Differential test: Settings reader validation should match domain validation."""
        # Test that domain validation errors are preserved
        invalid_paths = [
            ("relative/path", "must be an absolute path"),
            ("../etc/passwd", "path traversal"),
        ]

        for invalid_path, expected_error in invalid_paths:
            django_settings = {
                "MOUNT_PATH": invalid_path,
                "DATA_PATH": "/var/lib/litefs",
                "DATABASE_NAME": "db.sqlite3",
                "LEADER_ELECTION": "static",
                "PROXY_ADDR": ":8080",
                "ENABLED": True,
                "RETENTION": "1h",
                "PRIMARY_HOSTNAME": "node1",
            }
            with pytest.raises(LiteFSConfigError, match=expected_error):
                get_litefs_settings(django_settings)

    def test_validation_matches_domain_leader_election(self):
        """Differential test: Leader election validation matches domain."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "invalid",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "RAFT_SELF_ADDR": "localhost:4321",
            "RAFT_PEERS": ["node1:4321"],
        }
        with pytest.raises(LiteFSConfigError, match="leader_election"):
            get_litefs_settings(django_settings)

    def test_missing_required_field_raises_config_error(self):
        """Test that missing a single required field raises LiteFSConfigError (PROP-002)."""
        # Missing MOUNT_PATH
        django_settings = {
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
        }
        with pytest.raises(LiteFSConfigError, match="MOUNT_PATH"):
            get_litefs_settings(django_settings)

    def test_missing_multiple_required_fields_lists_all(self):
        """Test that missing multiple required fields lists all of them (PROP-002)."""
        # Missing MOUNT_PATH and DATA_PATH
        django_settings = {
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
        }
        with pytest.raises(LiteFSConfigError) as exc_info:
            get_litefs_settings(django_settings)
        error_message = str(exc_info.value)
        assert "DATA_PATH" in error_message
        assert "MOUNT_PATH" in error_message

    def test_empty_dict_raises_config_error_with_all_required_fields(self):
        """Test that empty dict raises LiteFSConfigError listing all 7 required fields (PROP-002)."""
        django_settings = {}
        with pytest.raises(LiteFSConfigError) as exc_info:
            get_litefs_settings(django_settings)
        error_message = str(exc_info.value)
        # All 7 required fields should be mentioned
        for field in ["MOUNT_PATH", "DATA_PATH", "DATABASE_NAME", "LEADER_ELECTION",
                      "PROXY_ADDR", "ENABLED", "RETENTION"]:
            assert field in error_message, f"Expected {field} in error message"

    def test_unknown_keys_are_silently_ignored(self):
        """Test that unknown Django settings keys are silently ignored (PROP-001 - intended behavior)."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
            "UNKNOWN_KEY": "should be ignored",
            "ANOTHER_UNKNOWN": 12345,
        }
        # Should not raise - unknown keys are silently ignored
        settings = get_litefs_settings(django_settings)
        assert settings.mount_path == "/litefs"
        assert settings.enabled is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestStaticLeaderConfigParsing:
    """Test parsing of static leader election configuration from Django settings."""

    def test_parse_static_leader_config_when_leader_election_is_static(self):
        """Test that StaticLeaderConfig is created when leader_election is 'static'."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1",
        }
        settings = get_litefs_settings(django_settings)
        assert settings.static_leader_config is not None
        assert isinstance(settings.static_leader_config, StaticLeaderConfig)
        assert settings.static_leader_config.primary_hostname == "node1"

    def test_static_leader_config_created_from_primary_hostname_key(self):
        """Test that PRIMARY_HOSTNAME key is used to create StaticLeaderConfig."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "primary.example.com",
        }
        settings = get_litefs_settings(django_settings)
        assert settings.static_leader_config.primary_hostname == "primary.example.com"

    def test_missing_primary_hostname_raises_error_when_static(self):
        """Test that missing PRIMARY_HOSTNAME raises helpful error when leader_election is 'static'."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            # Missing PRIMARY_HOSTNAME
        }
        with pytest.raises(LiteFSConfigError, match="PRIMARY_HOSTNAME"):
            get_litefs_settings(django_settings)

    def test_static_leader_config_none_when_raft_mode(self):
        """Test that static_leader_config is None when leader_election is 'raft'."""
        django_settings = {
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
        settings = get_litefs_settings(django_settings)
        assert settings.static_leader_config is None

    def test_raft_mode_does_not_require_primary_hostname(self):
        """Test that PRIMARY_HOSTNAME is not required when leader_election is 'raft'."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "raft",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "RAFT_SELF_ADDR": "localhost:4321",
            "RAFT_PEERS": ["node1:4321", "node2:4321"],
            # No PRIMARY_HOSTNAME required
        }
        # Should not raise
        settings = get_litefs_settings(django_settings)
        assert settings.leader_election == "raft"
        assert settings.static_leader_config is None

    def test_primary_hostname_validation_propagates_errors(self):
        """Test that StaticLeaderConfig validation errors are propagated."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "",  # Invalid: empty hostname
        }
        with pytest.raises(LiteFSConfigError, match="cannot be empty"):
            get_litefs_settings(django_settings)

    def test_primary_hostname_with_whitespace_rejected(self):
        """Test that PRIMARY_HOSTNAME with leading/trailing whitespace is rejected."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": " node1",  # Invalid: leading whitespace
        }
        with pytest.raises(LiteFSConfigError, match="leading/trailing whitespace"):
            get_litefs_settings(django_settings)

    def test_primary_hostname_with_control_chars_rejected(self):
        """Test that PRIMARY_HOSTNAME with control characters is rejected."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "node1\x00",  # Invalid: null byte
        }
        with pytest.raises(LiteFSConfigError, match="control characters"):
            get_litefs_settings(django_settings)

    def test_static_config_with_valid_fqdn(self):
        """Test that valid FQDN is accepted for PRIMARY_HOSTNAME."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": "primary-node.example.com",
        }
        settings = get_litefs_settings(django_settings)
        assert settings.static_leader_config.primary_hostname == "primary-node.example.com"

    @pytest.mark.tier(3)
    @given(
        hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,  # Start after control chars and space
                max_codepoint=126,  # End before DEL
                blacklist_characters=" \t\n\r",  # Exclude whitespace
            ),
            min_size=1,
            max_size=253,
        )
    )
    def test_round_trip_static_leader_config_pbt(self, hostname):
        """PBT: Valid hostnames round-trip correctly through Django settings reader."""
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": hostname,
        }
        settings = get_litefs_settings(django_settings)

        assert settings.static_leader_config is not None
        assert settings.static_leader_config.primary_hostname == hostname

    @pytest.mark.tier(3)
    @given(
        hostname_base=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        ),
        control_char=st.sampled_from(["\x00", "\x01", "\x1f", "\x7f", "\n", "\t"]),
    )
    def test_static_config_validation_rejects_control_chars_pbt(
        self, hostname_base, control_char
    ):
        """PBT: StaticLeaderConfig validation rejects hostnames with control characters."""
        hostname_with_control = hostname_base + control_char
        django_settings = {
            "MOUNT_PATH": "/litefs",
            "DATA_PATH": "/var/lib/litefs",
            "DATABASE_NAME": "db.sqlite3",
            "LEADER_ELECTION": "static",
            "PROXY_ADDR": ":8080",
            "ENABLED": True,
            "RETENTION": "1h",
            "PRIMARY_HOSTNAME": hostname_with_control,
        }
        with pytest.raises(LiteFSConfigError):
            get_litefs_settings(django_settings)
