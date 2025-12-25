"""Unit tests for FastAPI settings reader."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.domain.exceptions import LiteFSConfigError
from litefs_fastapi.settings import get_litefs_settings


@pytest.mark.unit
class TestFastAPISettingsReader:
    """Test FastAPI settings reader."""

    def test_convert_pydantic_settings_to_litefs_settings(self):
        """Test basic conversion from Pydantic settings to LiteFSSettings."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
        }
        settings = get_litefs_settings(pydantic_settings)
        assert isinstance(settings, LiteFSSettings)
        assert settings.mount_path == "/litefs"
        assert settings.data_path == "/var/lib/litefs"
        assert settings.database_name == "db.sqlite3"
        assert settings.leader_election == "static"
        assert settings.proxy_addr == ":8080"
        assert settings.enabled is True
        assert settings.retention == "1h"

    def test_snake_case_mapping_to_domain_fields(self):
        """Test that snake_case Pydantic keys map to domain fields."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
            "raft_self_addr": "localhost:4321",
            "raft_peers": ["node1:4321", "node2:4321"],
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.raft_self_addr == "localhost:4321"
        assert settings.raft_peers == ["node1:4321", "node2:4321"]

    def test_optional_fields_with_none(self):
        """Test that optional fields can be None."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
            "raft_self_addr": None,
            "raft_peers": None,
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.raft_self_addr is None
        assert settings.raft_peers is None

    def test_optional_fields_missing(self):
        """Test that optional fields can be missing from dict."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.raft_self_addr is None
        assert settings.raft_peers is None

    def test_validation_delegates_to_domain(self):
        """Test that validation errors from domain are raised."""
        pydantic_settings = {
            "mount_path": "../../etc/passwd",  # Invalid path traversal
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
        }
        with pytest.raises(LiteFSConfigError, match="path traversal"):
            get_litefs_settings(pydantic_settings)

    @pytest.mark.property
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
        """Property-based test: Pydantic dict → LiteFSSettings → Pydantic dict should be idempotent."""
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

        pydantic_settings = {
            "mount_path": mount_path,
            "data_path": data_path,
            "database_name": database_name,
            "leader_election": leader_election,
            "proxy_addr": proxy_addr,
            "enabled": enabled,
            "retention": retention,
        }
        # Only add primary_hostname if in static mode
        if leader_election == "static" and primary_hostname is not None:
            pydantic_settings["primary_hostname"] = primary_hostname
        if raft_self_addr is not None:
            pydantic_settings["raft_self_addr"] = raft_self_addr
        if raft_peers is not None:
            pydantic_settings["raft_peers"] = raft_peers

        # Convert to domain
        settings = get_litefs_settings(pydantic_settings)

        # Convert back to Pydantic dict format
        converted_back = {
            "mount_path": settings.mount_path,
            "data_path": settings.data_path,
            "database_name": settings.database_name,
            "leader_election": settings.leader_election,
            "proxy_addr": settings.proxy_addr,
            "enabled": settings.enabled,
            "retention": settings.retention,
        }
        # Only include primary_hostname if it was in the original
        if "primary_hostname" in pydantic_settings:
            if settings.static_leader_config is not None:
                converted_back["primary_hostname"] = settings.static_leader_config.primary_hostname
        if settings.raft_self_addr is not None:
            converted_back["raft_self_addr"] = settings.raft_self_addr
        if settings.raft_peers is not None:
            converted_back["raft_peers"] = settings.raft_peers

        # Check idempotence
        assert converted_back["mount_path"] == pydantic_settings["mount_path"]
        assert converted_back["data_path"] == pydantic_settings["data_path"]
        assert converted_back["database_name"] == pydantic_settings["database_name"]
        assert converted_back["leader_election"] == pydantic_settings["leader_election"]
        assert converted_back["proxy_addr"] == pydantic_settings["proxy_addr"]
        assert converted_back["enabled"] == pydantic_settings["enabled"]
        assert converted_back["retention"] == pydantic_settings["retention"]
        assert converted_back.get("primary_hostname") == pydantic_settings.get("primary_hostname")
        assert converted_back.get("raft_self_addr") == pydantic_settings.get("raft_self_addr")
        assert converted_back.get("raft_peers") == pydantic_settings.get("raft_peers")

    def test_validation_matches_domain_absolute_paths(self):
        """Differential test: Settings reader validation should match domain validation."""
        # Test that domain validation errors are preserved
        invalid_paths = [
            ("relative/path", "must be an absolute path"),
            ("../etc/passwd", "path traversal"),
        ]

        for invalid_path, expected_error in invalid_paths:
            pydantic_settings = {
                "mount_path": invalid_path,
                "data_path": "/var/lib/litefs",
                "database_name": "db.sqlite3",
                "leader_election": "static",
                "proxy_addr": ":8080",
                "enabled": True,
                "retention": "1h",
                "primary_hostname": "node1",
            }
            with pytest.raises(LiteFSConfigError, match=expected_error):
                get_litefs_settings(pydantic_settings)

    def test_validation_matches_domain_leader_election(self):
        """Differential test: Leader election validation matches domain."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "invalid",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "raft_self_addr": "localhost:4321",
            "raft_peers": ["node1:4321"],
        }
        with pytest.raises(LiteFSConfigError, match="leader_election"):
            get_litefs_settings(pydantic_settings)

    def test_missing_required_field_raises_config_error(self):
        """Test that missing a single required field raises LiteFSConfigError."""
        # Missing mount_path
        pydantic_settings = {
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
        }
        with pytest.raises(LiteFSConfigError, match="mount_path"):
            get_litefs_settings(pydantic_settings)

    def test_missing_multiple_required_fields_lists_all(self):
        """Test that missing multiple required fields lists all of them."""
        # Missing mount_path and data_path
        pydantic_settings = {
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
        }
        with pytest.raises(LiteFSConfigError) as exc_info:
            get_litefs_settings(pydantic_settings)
        error_message = str(exc_info.value)
        assert "data_path" in error_message
        assert "mount_path" in error_message

    def test_empty_dict_raises_config_error_with_all_required_fields(self):
        """Test that empty dict raises LiteFSConfigError listing all 7 required fields."""
        pydantic_settings: dict[str, str | bool | list[str] | None] = {}
        with pytest.raises(LiteFSConfigError) as exc_info:
            get_litefs_settings(pydantic_settings)
        error_message = str(exc_info.value)
        # All 7 required fields should be mentioned
        for field in ["mount_path", "data_path", "database_name", "leader_election",
                      "proxy_addr", "enabled", "retention"]:
            assert field in error_message, f"Expected {field} in error message"

    def test_unknown_keys_are_silently_ignored(self):
        """Test that unknown Pydantic settings keys are silently ignored."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
            "unknown_key": "should be ignored",
            "another_unknown": 12345,
        }
        # Should not raise - unknown keys are silently ignored
        settings = get_litefs_settings(pydantic_settings)
        assert settings.mount_path == "/litefs"
        assert settings.enabled is True


@pytest.mark.unit
class TestStaticLeaderConfigParsing:
    """Test parsing of static leader election configuration from Pydantic settings."""

    def test_parse_static_leader_config_when_leader_election_is_static(self):
        """Test that StaticLeaderConfig is created when leader_election is 'static'."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1",
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.static_leader_config is not None
        assert isinstance(settings.static_leader_config, StaticLeaderConfig)
        assert settings.static_leader_config.primary_hostname == "node1"

    def test_static_leader_config_created_from_primary_hostname_key(self):
        """Test that primary_hostname key is used to create StaticLeaderConfig."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "primary.example.com",
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.static_leader_config.primary_hostname == "primary.example.com"

    def test_missing_primary_hostname_raises_error_when_static(self):
        """Test that missing primary_hostname raises helpful error when leader_election is 'static'."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            # Missing primary_hostname
        }
        with pytest.raises(LiteFSConfigError, match="primary_hostname"):
            get_litefs_settings(pydantic_settings)

    def test_static_leader_config_none_when_raft_mode(self):
        """Test that static_leader_config is None when leader_election is 'raft'."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "raft",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "raft_self_addr": "localhost:4321",
            "raft_peers": ["node1:4321", "node2:4321"],
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.static_leader_config is None

    def test_raft_mode_does_not_require_primary_hostname(self):
        """Test that primary_hostname is not required when leader_election is 'raft'."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "raft",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "raft_self_addr": "localhost:4321",
            "raft_peers": ["node1:4321", "node2:4321"],
            # No primary_hostname required
        }
        # Should not raise
        settings = get_litefs_settings(pydantic_settings)
        assert settings.leader_election == "raft"
        assert settings.static_leader_config is None

    def test_primary_hostname_validation_propagates_errors(self):
        """Test that StaticLeaderConfig validation errors are propagated."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "",  # Invalid: empty hostname
        }
        with pytest.raises(LiteFSConfigError, match="cannot be empty"):
            get_litefs_settings(pydantic_settings)

    def test_primary_hostname_with_whitespace_rejected(self):
        """Test that primary_hostname with leading/trailing whitespace is rejected."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": " node1",  # Invalid: leading whitespace
        }
        with pytest.raises(LiteFSConfigError, match="leading/trailing whitespace"):
            get_litefs_settings(pydantic_settings)

    def test_primary_hostname_with_control_chars_rejected(self):
        """Test that primary_hostname with control characters is rejected."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "node1\x00",  # Invalid: null byte
        }
        with pytest.raises(LiteFSConfigError, match="control characters"):
            get_litefs_settings(pydantic_settings)

    def test_static_config_with_valid_fqdn(self):
        """Test that valid FQDN is accepted for primary_hostname."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": "primary-node.example.com",
        }
        settings = get_litefs_settings(pydantic_settings)
        assert settings.static_leader_config.primary_hostname == "primary-node.example.com"

    @pytest.mark.property
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
    def test_round_trip_static_leader_config_pbt(self, hostname: str) -> None:
        """PBT: Valid hostnames round-trip correctly through FastAPI settings reader."""
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": hostname,
        }
        settings = get_litefs_settings(pydantic_settings)

        assert settings.static_leader_config is not None
        assert settings.static_leader_config.primary_hostname == hostname

    @pytest.mark.property
    @given(
        hostname_base=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        ),
        control_char=st.sampled_from(["\x00", "\x01", "\x1f", "\x7f", "\n", "\t"]),
    )
    def test_static_config_validation_rejects_control_chars_pbt(
        self, hostname_base: str, control_char: str
    ) -> None:
        """PBT: StaticLeaderConfig validation rejects hostnames with control characters."""
        hostname_with_control = hostname_base + control_char
        pydantic_settings = {
            "mount_path": "/litefs",
            "data_path": "/var/lib/litefs",
            "database_name": "db.sqlite3",
            "leader_election": "static",
            "proxy_addr": ":8080",
            "enabled": True,
            "retention": "1h",
            "primary_hostname": hostname_with_control,
        }
        with pytest.raises(LiteFSConfigError):
            get_litefs_settings(pydantic_settings)


@pytest.mark.unit
class TestZeroDjangoImports:
    """Test that FastAPI settings reader has zero Django imports."""

    def test_module_has_no_django_imports(self) -> None:
        """Test that the FastAPI settings module doesn't import Django."""
        import litefs_fastapi.settings as settings_module

        # Get the source code
        import inspect
        source = inspect.getsource(settings_module)

        # Check that Django is not imported anywhere
        assert "django" not in source.lower(), "FastAPI settings reader must not import Django"
        assert "from django" not in source, "FastAPI settings reader must not import Django"
        assert "import django" not in source, "FastAPI settings reader must not import Django"
