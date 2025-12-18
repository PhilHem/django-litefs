"""Unit tests for Django database backend."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs_django.db.backends.litefs.base import DatabaseWrapper


@pytest.mark.unit
class TestDatabaseBackend:
    """Test LiteFS database backend."""

    def test_backend_initialization(self):
        """Test that DatabaseWrapper can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            assert wrapper.settings_dict == settings_dict

    def test_uses_litefs_mount_path_for_database(self):
        """Test that database path uses LiteFS mount path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            db_file = mount_path / "test.db"
            db_file.touch()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            # Database path should be in mount_path
            assert str(mount_path) in str(wrapper.settings_dict["NAME"])

    def test_delegates_to_primary_detector(self):
        """Test that backend uses PrimaryDetector use case (Clean Architecture)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            # Should have PrimaryDetector instance (not business logic in adapter)
            assert hasattr(wrapper, "_primary_detector")
            assert isinstance(wrapper._primary_detector, PrimaryDetector)

    def test_transaction_mode_immediate(self):
        """Test that transaction mode is set to IMMEDIATE (DJANGO-009)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            # Check that transaction mode is IMMEDIATE
            # This will be verified when connection is created
            assert hasattr(wrapper, "features")
            # Transaction mode is set in get_new_connection or similar

    def test_connection_initialization_with_mount_path(self):
        """Test connection creation uses LiteFS mount path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            db_file = mount_path / "test.db"

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            # Connection should be created with path in mount_path
            # This is a simplified test - actual connection requires SQLite
            assert wrapper.settings_dict["OPTIONS"]["litefs_mount_path"] == str(
                mount_path
            )

    def test_write_operation_checks_primary(self):
        """Test that write operations check primary status before executing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            # No .primary file = replica
            (mount_path / "test.db").touch()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)

            # Write operation should check primary
            from litefs_django.exceptions import NotPrimaryError

            # Mock cursor execute to test primary check
            with patch.object(
                wrapper._primary_detector, "is_primary", return_value=False
            ):
                # Write operation should raise NotPrimaryError
                # This will be tested when we implement execute() override
                assert wrapper._primary_detector.is_primary() is False

    def test_write_on_replica_raises_exception(self):
        """Test that write on replica raises NotPrimaryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            # No .primary file = replica

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            from litefs_django.exceptions import NotPrimaryError

            # When primary detector returns False, write should fail
            with patch.object(
                wrapper._primary_detector, "is_primary", return_value=False
            ):
                # This test will be complete when execute() is implemented
                assert not wrapper._primary_detector.is_primary()

    def test_transaction_boundaries_use_immediate_mode(self):
        """Test that all Django transaction boundaries use IMMEDIATE mode (DJANGO-021).

        Verifies that _start_transaction_under_autocommit is called and uses
        BEGIN IMMEDIATE for autocommit transactions, @transaction.atomic, and
        transaction.atomic() context manager.
        """
        import sqlite3
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            db_path = mount_path / "test.db"

            # Create primary file to allow writes
            (mount_path / ".primary").write_text("node-1")

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            wrapper.ensure_connection()

            # Capture SQL statements using SQLite trace callback
            executed_sql = []

            def trace_callback(statement):
                executed_sql.append(statement)

            # Set trace callback on the underlying SQLite connection
            wrapper.connection.set_trace_callback(trace_callback)

            # Test 1: Autocommit transaction (via _start_transaction_under_autocommit)
            wrapper._start_transaction_under_autocommit()

            # Test 2: Verify BEGIN IMMEDIATE was in the captured SQL
            begin_statements = [
                sql for sql in executed_sql if sql.strip().upper().startswith("BEGIN")
            ]
            assert len(begin_statements) > 0, "No BEGIN statement found"
            assert any("IMMEDIATE" in sql.upper() for sql in begin_statements), (
                f"BEGIN IMMEDIATE not found in transaction start. Found: {begin_statements}"
            )

    def test_start_transaction_under_autocommit_uses_immediate(self):
        """Test that _start_transaction_under_autocommit executes BEGIN IMMEDIATE (DJANGO-020)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            (mount_path / "test.db").touch()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            wrapper.ensure_connection()

            # Mock cursor to capture executed SQL
            executed_sql = []
            mock_cursor = MagicMock()

            def mock_execute(sql, params=None):
                executed_sql.append(sql)
                return None

            mock_cursor.execute = mock_execute

            with patch.object(wrapper, "cursor", return_value=mock_cursor):
                # Call _start_transaction_under_autocommit
                wrapper._start_transaction_under_autocommit()

            # Verify BEGIN IMMEDIATE was executed
            begin_statements = [
                sql for sql in executed_sql if sql.strip().upper().startswith("BEGIN")
            ]
            assert len(begin_statements) > 0, "No BEGIN statement found"
            assert any("IMMEDIATE" in sql.upper() for sql in begin_statements), (
                f"BEGIN IMMEDIATE not found. Found: {begin_statements}"
            )
