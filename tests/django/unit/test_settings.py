"""Unit tests for Django settings reader."""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import patch

from litefs.domain.settings import LiteFSSettings, LiteFSConfigError
from litefs_django.settings import get_litefs_settings


@pytest.mark.unit
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
        }
        with pytest.raises(LiteFSConfigError, match="path traversal"):
            get_litefs_settings(django_settings)

    @pytest.mark.property
    @given(
        mount_path=st.just("/litefs"),
        data_path=st.just("/var/lib/litefs"),
        database_name=st.text(min_size=1, max_size=50),
        leader_election=st.sampled_from(["static", "raft"]),
        proxy_addr=st.text(min_size=1, max_size=50),
        enabled=st.booleans(),
        retention=st.text(min_size=1, max_size=20),
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
        raft_self_addr,
        raft_peers,
    ):
        """Property-based test: Django dict → LiteFSSettings → Django dict should be idempotent."""
        # Skip if values would fail domain validation
        if ".." in mount_path or ".." in data_path:
            return
        if not mount_path.startswith("/") or not data_path.startswith("/"):
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
        }
        with pytest.raises(LiteFSConfigError, match="leader_election"):
            get_litefs_settings(django_settings)
