"""Unit tests for LiteFSSettings domain entity."""

import pytest
from pathlib import Path
from hypothesis import given, strategies as st

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

    def test_reject_empty_database_name(self):
        """Test that empty database_name is rejected."""
        with pytest.raises(LiteFSConfigError, match="database_name cannot be empty"):
            LiteFSSettings(
                mount_path="/litefs",
                data_path="/var/lib/litefs",
                database_name="",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )

    def test_reject_whitespace_only_database_name(self):
        """Test that whitespace-only database_name is rejected."""
        with pytest.raises(LiteFSConfigError, match="database_name cannot be empty"):
            LiteFSSettings(
                mount_path="/litefs",
                data_path="/var/lib/litefs",
                database_name="   ",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )


@pytest.mark.unit
@pytest.mark.property
class TestDatabaseNameValidationPBT:
    """Property-based tests for database_name validation."""

    @given(
        database_name=st.text(
            alphabet=st.characters(
                min_codepoint=33,  # Start after space
                max_codepoint=126,  # Printable ASCII
                blacklist_characters=" \t\n\r",  # Exclude whitespace
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_non_whitespace_database_names_accepted(self, database_name):
        """PBT: Valid non-whitespace database names should be accepted."""
        settings = LiteFSSettings(
            mount_path="/litefs",
            data_path="/var/lib/litefs",
            database_name=database_name,
            leader_election="static",
            proxy_addr=":8080",
            enabled=True,
            retention="1h",
        )
        assert settings.database_name == database_name

    @given(
        whitespace=st.sampled_from([" ", "  ", "   ", "\t", " \t ", "\t\t"])
    )
    def test_whitespace_only_database_names_rejected(self, whitespace):
        """PBT: Whitespace-only database names should be rejected."""
        with pytest.raises(LiteFSConfigError):
            LiteFSSettings(
                mount_path="/litefs",
                data_path="/var/lib/litefs",
                database_name=whitespace,
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )


@pytest.mark.unit
@pytest.mark.property
class TestPathSanitizationPBT:
    """Property-based tests for path sanitization edge cases."""

    @given(path_component=st.text(min_size=1, max_size=50))
    def test_path_with_null_bytes_rejected(self, path_component):
        """PBT: Paths with null bytes should be rejected."""
        # Skip if path would fail other validations
        if ".." in path_component:
            return

        # Create path with null byte
        path_with_null = f"/litefs/{path_component}\x00/evil"

        # Pathlib.Path may handle null bytes differently, but validation should catch it
        # Check if Path raises ValueError when constructed with null byte
        try:
            Path(path_with_null)
            # If Path construction succeeds, our validation should still reject it
            with pytest.raises(LiteFSConfigError):
                LiteFSSettings(
                    mount_path=path_with_null,
                    data_path="/var/lib/litefs",
                    database_name="db.sqlite3",
                    leader_election="static",
                    proxy_addr=":8080",
                    enabled=True,
                    retention="1h",
                )
        except ValueError:
            # Pathlib rejects null bytes - this is acceptable behavior
            pass

    @given(
        path_suffix=st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=50,
        )
    )
    def test_unicode_paths_validated(self, path_suffix):
        """PBT: Unicode paths should be validated correctly."""
        # Skip if contains path traversal (can't use blacklist_characters for multi-char)
        if ".." in path_suffix:
            return

        # Skip if not absolute path
        if not path_suffix.startswith("/"):
            path_suffix = f"/litefs/{path_suffix}"

        # Should either succeed or raise appropriate error
        try:
            settings = LiteFSSettings(
                mount_path=path_suffix,
                data_path="/var/lib/litefs",
                database_name="db.sqlite3",
                leader_election="static",
                proxy_addr=":8080",
                enabled=True,
                retention="1h",
            )
            # If successful, path should be preserved
            assert settings.mount_path == path_suffix
        except LiteFSConfigError:
            # If validation fails, should be for a valid reason
            pass




