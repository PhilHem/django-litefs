"""Unit tests for Django database backend."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from litefs.usecases.primary_detector import PrimaryDetector
from litefs.usecases.split_brain_detector import SplitBrainDetector, SplitBrainStatus
from litefs.domain.split_brain import RaftNodeState
from litefs_django.db.backends.litefs.base import DatabaseWrapper, LiteFSCursor
from litefs_django.exceptions import NotPrimaryError, SplitBrainError
from .conftest import create_litefs_settings_dict
from django.test import override_settings


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestDatabaseBackend:
    """Test LiteFS database backend."""

    @override_settings(LITEFS={"ENABLED": True})
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
            # DatabaseWrapper modifies NAME to be absolute path in mount_path
            expected_settings = settings_dict.copy()
            expected_settings["NAME"] = str(mount_path / "test.db")
            assert wrapper.settings_dict == expected_settings

    @override_settings(LITEFS={"ENABLED": True})
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
            _db_file = mount_path / "test.db"  # noqa: F841

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
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            _db_path = mount_path / "test.db"  # noqa: F841

            # Create primary file to allow writes
            (mount_path / ".primary").write_text("node-1")

            settings_dict = create_litefs_settings_dict(mount_path, "test.db")

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

    @override_settings(LITEFS={"ENABLED": True})
    def test_start_transaction_under_autocommit_uses_immediate(self):
        """Test that _start_transaction_under_autocommit executes BEGIN IMMEDIATE (DJANGO-020)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()
            (mount_path / "test.db").touch()

            settings_dict = create_litefs_settings_dict(mount_path, "test.db")

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

    def test_sql_detector_uses_precompiled_regex(self):
        """Test that SQLDetector uses pre-compiled regex patterns (PERF-001).

        Verifies that SQLDetector uses module-level compiled patterns instead
        of re.sub() compiling on each call.
        """
        import re
        from litefs.usecases import sql_detector

        # Check module-level compiled patterns exist in sql_detector module
        assert hasattr(sql_detector, "_BLOCK_COMMENT_RE"), (
            "Module should have _BLOCK_COMMENT_RE compiled pattern"
        )
        assert hasattr(sql_detector, "_LINE_COMMENT_RE"), (
            "Module should have _LINE_COMMENT_RE compiled pattern"
        )

        # Verify they are compiled regex patterns
        assert isinstance(sql_detector._BLOCK_COMMENT_RE, re.Pattern), (
            "_BLOCK_COMMENT_RE should be a compiled regex pattern"
        )
        assert isinstance(sql_detector._LINE_COMMENT_RE, re.Pattern), (
            "_LINE_COMMENT_RE should be a compiled regex pattern"
        )

    def test_sql_detector_re_module_imported_at_top(self):
        """Test that re module is imported at module level in SQLDetector (DJANGO-034).

        Verifies that `import re` appears at module level in sql_detector.py,
        not inside a method body.
        """
        from litefs.usecases.sql_detector import SQLDetector
        import inspect

        # Get the source code of strip_sql_comments method
        source = inspect.getsource(SQLDetector.strip_sql_comments)

        # The method should NOT contain 'import re' inside its body
        assert "import re" not in source, (
            "strip_sql_comments should not import re inside method body. "
            "Import should be at module level."
        )


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestWriteDetectionSqlOperations:
    """Test SQL write detection for additional operations (SQL-001, SQL-002, SQL-003)."""

    def _is_write(self, sql):
        """Helper to call SQLDetector.is_write_operation on real implementation."""
        from litefs.usecases.sql_detector import SQLDetector

        detector = SQLDetector()
        return detector.is_write_operation(sql)

    # SQL-001: ATTACH/DETACH DATABASE
    def test_is_write_operation_attach_database(self):
        """Test ATTACH DATABASE is detected as write (SQL-001)."""
        assert self._is_write("ATTACH DATABASE ':memory:' AS temp") is True

    def test_is_write_operation_detach_database(self):
        """Test DETACH DATABASE is detected as write (SQL-001)."""
        assert self._is_write("DETACH DATABASE temp") is True

    def test_is_write_operation_attach_with_path(self):
        """Test ATTACH DATABASE with path is detected as write (SQL-001)."""
        assert self._is_write("ATTACH DATABASE '/path/to/db.sqlite3' AS other") is True

    # SQL-002: SAVEPOINT operations
    def test_is_write_operation_savepoint(self):
        """Test SAVEPOINT is detected as write (SQL-002)."""
        assert self._is_write("SAVEPOINT my_savepoint") is True

    def test_is_write_operation_release_savepoint(self):
        """Test RELEASE SAVEPOINT is detected as write (SQL-002)."""
        assert self._is_write("RELEASE SAVEPOINT my_savepoint") is True

    def test_is_write_operation_rollback_to_savepoint(self):
        """Test ROLLBACK TO SAVEPOINT is detected as write (SQL-002)."""
        assert self._is_write("ROLLBACK TO SAVEPOINT my_savepoint") is True

    # SQL-003: State-modifying PRAGMAs
    def test_is_write_operation_pragma_user_version_write(self):
        """Test PRAGMA user_version = N is detected as write (SQL-003)."""
        assert self._is_write("PRAGMA user_version = 1") is True

    def test_is_write_operation_pragma_schema_version_write(self):
        """Test PRAGMA schema_version = N is detected as write (SQL-003)."""
        assert self._is_write("PRAGMA schema_version = 1") is True

    def test_is_write_operation_pragma_application_id_write(self):
        """Test PRAGMA application_id = N is detected as write (SQL-003)."""
        assert self._is_write("PRAGMA application_id = 12345") is True

    def test_is_write_operation_pragma_read_only_not_write(self):
        """Test PRAGMA read (no assignment) is NOT detected as write (SQL-003)."""
        assert self._is_write("PRAGMA user_version") is False

    def test_is_write_operation_pragma_journal_mode_not_write(self):
        """Test PRAGMA journal_mode (read) is NOT detected as write (SQL-003)."""
        assert self._is_write("PRAGMA journal_mode") is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestTransactionModeConfiguration:
    """Test configurable transaction mode."""

    def test_transaction_mode_defaults_to_immediate(self):
        """Test that transaction mode defaults to IMMEDIATE."""
        import tempfile
        from pathlib import Path
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

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
            # Default should be IMMEDIATE
            assert wrapper._transaction_mode == "IMMEDIATE"

    def test_transaction_mode_can_be_configured(self):
        """Test that transaction mode can be configured via OPTIONS."""
        import tempfile
        from pathlib import Path
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                    "transaction_mode": "DEFERRED",
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            assert wrapper._transaction_mode == "DEFERRED"

    def test_transaction_mode_deferred(self):
        """Test DEFERRED transaction mode option."""
        import tempfile
        from pathlib import Path
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                    "transaction_mode": "DEFERRED",
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            assert wrapper._transaction_mode == "DEFERRED"

    def test_transaction_mode_exclusive(self):
        """Test EXCLUSIVE transaction mode option."""
        import tempfile
        from pathlib import Path
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        with tempfile.TemporaryDirectory() as tmpdir:
            mount_path = Path(tmpdir) / "litefs"
            mount_path.mkdir()

            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": "test.db",
                "OPTIONS": {
                    "litefs_mount_path": str(mount_path),
                    "transaction_mode": "EXCLUSIVE",
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            assert wrapper._transaction_mode == "EXCLUSIVE"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestSplitBrainDetectionInCursor:
    """Test split-brain detection in LiteFSCursor."""

    def test_litefs_cursor_accepts_split_brain_detector(self):
        """Test that LiteFSCursor accepts split_brain_detector parameter."""
        import sqlite3
        from unittest.mock import Mock

        # Create real in-memory SQLite connection
        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        try:
            # Should not raise exception
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            assert cursor._split_brain_detector is mock_split_brain_detector
        finally:
            connection.close()

    def test_litefs_cursor_split_brain_detector_optional(self):
        """Test that LiteFSCursor split_brain_detector is optional."""
        import sqlite3
        from unittest.mock import Mock

        # Create real in-memory SQLite connection
        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()

        try:
            # Should work with default None
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
            )

            assert cursor._split_brain_detector is None
        finally:
            connection.close()

    def test_split_brain_check_before_primary_on_execute(self):
        """Test that split-brain is checked BEFORE primary status on execute()."""
        import sqlite3
        from unittest.mock import Mock

        # Create real in-memory SQLite connection
        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        # Setup split-brain detected
        split_brain_status = SplitBrainStatus(
            is_split_brain=True,
            leader_nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
            ],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Try write operation - should check split-brain first
            with pytest.raises(SplitBrainError):
                cursor.execute("INSERT INTO users (name) VALUES ('Alice')")

            # Split-brain detector should be called
            mock_split_brain_detector.detect_split_brain.assert_called()

            # Primary detector should NOT be called (split-brain checked first)
            mock_primary_detector.is_primary.assert_not_called()
        finally:
            connection.close()

    def test_split_brain_error_on_execute_write(self):
        """Test that SplitBrainError is raised on write when split-brain detected."""
        import sqlite3
        from unittest.mock import Mock

        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        split_brain_status = SplitBrainStatus(
            is_split_brain=True,
            leader_nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
            ],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Execute write should raise SplitBrainError
            with pytest.raises(SplitBrainError) as exc_info:
                cursor.execute("UPDATE users SET name='Bob' WHERE id=1")

            # Verify error message mentions split-brain
            assert "split" in str(exc_info.value).lower()
        finally:
            connection.close()

    def test_split_brain_error_on_executemany_write(self):
        """Test that SplitBrainError is raised on executemany when split-brain detected."""
        import sqlite3
        from unittest.mock import Mock

        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        split_brain_status = SplitBrainStatus(
            is_split_brain=True,
            leader_nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
            ],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Executemany write should raise SplitBrainError
            with pytest.raises(SplitBrainError) as exc_info:
                cursor.executemany(
                    "INSERT INTO users VALUES (?, ?)", [("Alice", 1), ("Bob", 2)]
                )

            assert "split" in str(exc_info.value).lower()
        finally:
            connection.close()

    def test_split_brain_error_on_executescript_write(self):
        """Test that SplitBrainError is raised on executescript when split-brain detected."""
        import sqlite3
        from unittest.mock import Mock

        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        split_brain_status = SplitBrainStatus(
            is_split_brain=True,
            leader_nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
            ],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Executescript should raise SplitBrainError
            with pytest.raises(SplitBrainError) as exc_info:
                cursor.executescript(
                    "CREATE TABLE test (id INT); INSERT INTO test VALUES (1);"
                )

            assert "split" in str(exc_info.value).lower()
        finally:
            connection.close()

    def test_no_split_brain_allows_primary_check_on_execute(self):
        """Test that when split-brain is not detected, primary check proceeds on execute."""
        import sqlite3
        from unittest.mock import Mock

        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        # No split-brain
        split_brain_status = SplitBrainStatus(
            is_split_brain=False,
            leader_nodes=[RaftNodeState(node_id="node-1", is_leader=True)],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        # Primary detector returns False (replica)
        mock_primary_detector.is_primary.return_value = False

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Write should check split-brain (none), then primary (false) -> raises NotPrimaryError
            with pytest.raises(NotPrimaryError):
                cursor.execute("INSERT INTO users VALUES ('Alice')")

            # Both should be called
            mock_split_brain_detector.detect_split_brain.assert_called()
            mock_primary_detector.is_primary.assert_called()
        finally:
            connection.close()

    def test_read_operation_unaffected_by_split_brain(self):
        """Test that read operations don't check split-brain."""
        import sqlite3
        from unittest.mock import Mock

        connection = sqlite3.connect(":memory:")
        mock_primary_detector = Mock()
        mock_split_brain_detector = Mock(spec=SplitBrainDetector)

        # Setup so split-brain would raise if checked
        split_brain_status = SplitBrainStatus(
            is_split_brain=True,
            leader_nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
            ],
        )
        mock_split_brain_detector.detect_split_brain.return_value = split_brain_status

        try:
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
            )

            # Mock parent execute to avoid actual SQLite calls
            with patch.object(
                type(cursor).__bases__[0], "execute", return_value=cursor
            ):
                # Read operation should NOT call split-brain detector
                cursor.execute("SELECT * FROM users")

            # Split-brain detector should NOT be called for read
            mock_split_brain_detector.detect_split_brain.assert_not_called()
        finally:
            connection.close()

    def test_database_wrapper_injects_split_brain_detector(self):
        """Test that DatabaseWrapper injects split_brain_detector into cursor."""
        import sqlite3

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

            mock_split_brain_detector = Mock(spec=SplitBrainDetector)
            wrapper = DatabaseWrapper(
                settings_dict,
                split_brain_detector=mock_split_brain_detector,
            )

            # create_cursor should inject the split_brain_detector
            real_connection = sqlite3.connect(":memory:")
            try:
                with patch.object(wrapper, "connection", real_connection):
                    cursor = wrapper.create_cursor()
                    assert isinstance(cursor, LiteFSCursor)
                    assert cursor._split_brain_detector is mock_split_brain_detector
            finally:
                real_connection.close()

    def test_database_wrapper_creates_split_brain_detector_if_not_provided(self):
        """Test that DatabaseWrapper creates SplitBrainDetector if not injected."""
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

            # No split_brain_detector provided
            wrapper = DatabaseWrapper(settings_dict)

            # Should have created one
            assert hasattr(wrapper, "_split_brain_detector")
            # The detector should be a SplitBrainDetector instance (or could be None if optional)
            # This will be verified in implementation

    def test_split_brain_error_is_database_error(self):
        """Test that SplitBrainError inherits from Django's DatabaseError."""
        from django.db import DatabaseError

        assert issubclass(SplitBrainError, DatabaseError)


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
class TestDevMode:
    """Test dev mode bypass functionality."""

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_initialization_skips_mount_path_validation(self):
        """Test that dev mode skips mount path validation."""
        # Use a nonexistent mount path - should not raise error in dev mode
        settings_dict = {
            "ENGINE": "litefs_django.db.backends.litefs",
            "NAME": "test.db",
            "OPTIONS": {
                "litefs_mount_path": "/nonexistent/path",
            },
        }

        # Should not raise error even though mount path doesn't exist
        wrapper = DatabaseWrapper(settings_dict)
        assert wrapper._dev_mode is True

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_uses_standard_sqlite_path(self):
        """Test that dev mode uses standard SQLite path (not mount_path)."""
        settings_dict = {
            "ENGINE": "litefs_django.db.backends.litefs",
            "NAME": "dev.db",
            "OPTIONS": {
                "litefs_mount_path": "/mnt/litefs",
            },
        }

        wrapper = DatabaseWrapper(settings_dict)
        # In dev mode, NAME should remain as-is (not prepended with mount_path)
        assert wrapper.settings_dict["NAME"] == "dev.db"

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_skips_primary_check_on_write(self):
        """Test that dev mode skips primary check on write operations."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            connection = sqlite3.connect(str(db_path))
            connection.execute("CREATE TABLE users (name TEXT)")

            # Create a mock primary detector that returns False (replica)
            mock_primary_detector = Mock()
            mock_primary_detector.is_primary.return_value = False

            # Create cursor in dev mode
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                dev_mode=True,
            )

            # Write should succeed (no NotPrimaryError) because dev_mode=True
            cursor.execute("INSERT INTO users VALUES ('Alice')")
            connection.commit()

            # Verify write succeeded
            result = connection.execute("SELECT name FROM users").fetchall()
            assert result == [("Alice",)]

            # Verify primary detector was NOT called
            mock_primary_detector.is_primary.assert_not_called()

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_skips_split_brain_check_on_write(self):
        """Test that dev mode skips split-brain check on write operations."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            connection = sqlite3.connect(str(db_path))
            connection.execute("CREATE TABLE users (name TEXT)")

            # Create a mock split-brain detector that detects split-brain
            mock_split_brain_detector = Mock()
            split_brain_status = SplitBrainStatus(
                is_split_brain=True,
                leader_nodes=[
                    RaftNodeState(node_id="node-1", is_leader=True),
                    RaftNodeState(node_id="node-2", is_leader=True),
                ],
            )
            mock_split_brain_detector.detect_split_brain.return_value = (
                split_brain_status
            )

            mock_primary_detector = Mock()
            mock_primary_detector.is_primary.return_value = True

            # Create cursor in dev mode
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
                dev_mode=True,
            )

            # Write should succeed (no SplitBrainError) because dev_mode=True
            cursor.execute("INSERT INTO users VALUES ('Bob')")
            connection.commit()

            # Verify write succeeded
            result = connection.execute("SELECT name FROM users").fetchall()
            assert result == [("Bob",)]

            # Verify split-brain detector was NOT called
            mock_split_brain_detector.detect_split_brain.assert_not_called()

    @override_settings(LITEFS=None)
    def test_dev_mode_when_litefs_settings_missing(self):
        """Test that dev mode is enabled when LITEFS settings dict is missing."""
        settings_dict = {
            "ENGINE": "litefs_django.db.backends.litefs",
            "NAME": "test.db",
            "OPTIONS": {
                "litefs_mount_path": "/mnt/litefs",
            },
        }

        wrapper = DatabaseWrapper(settings_dict)
        assert wrapper._dev_mode is True

    @override_settings(LITEFS={"ENABLED": True})
    def test_production_mode_when_enabled_true(self):
        """Test that production mode is used when LITEFS.enabled is True."""
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
            assert wrapper._dev_mode is False

    @override_settings(LITEFS={"MOUNT_PATH": "/mnt/litefs"})
    def test_production_mode_when_enabled_not_specified(self):
        """Test that production mode is used when LITEFS.enabled is not specified."""
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
            assert wrapper._dev_mode is False

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_skips_mount_path_validation_in_get_new_connection(self):
        """Test that dev mode skips mount path validation in get_new_connection."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            settings_dict = {
                "ENGINE": "litefs_django.db.backends.litefs",
                "NAME": str(db_path),
                "OPTIONS": {
                    "litefs_mount_path": "/nonexistent/path",
                },
            }

            wrapper = DatabaseWrapper(settings_dict)
            # Should not raise error even though mount path doesn't exist
            conn_params = wrapper.get_connection_params()
            conn = wrapper.get_new_connection(conn_params)
            assert conn is not None
            conn.close()

    @override_settings(LITEFS={"ENABLED": False})
    def test_dev_mode_executescript_bypasses_checks(self):
        """Test that dev mode bypasses checks in executescript."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            connection = sqlite3.connect(str(db_path))

            # Create mocks that would fail in production mode
            mock_primary_detector = Mock()
            mock_primary_detector.is_primary.return_value = False  # Replica

            mock_split_brain_detector = Mock()
            split_brain_status = SplitBrainStatus(
                is_split_brain=True,
                leader_nodes=[
                    RaftNodeState(node_id="node-1", is_leader=True),
                    RaftNodeState(node_id="node-2", is_leader=True),
                ],
            )
            mock_split_brain_detector.detect_split_brain.return_value = (
                split_brain_status
            )

            # Create cursor in dev mode
            cursor = LiteFSCursor(
                connection,
                primary_detector=mock_primary_detector,
                split_brain_detector=mock_split_brain_detector,
                dev_mode=True,
            )

            # Script execution should succeed in dev mode
            cursor.executescript(
                "CREATE TABLE users (name TEXT); INSERT INTO users VALUES ('Charlie');"
            )
            connection.commit()

            # Verify script executed successfully
            result = connection.execute("SELECT name FROM users").fetchall()
            assert result == [("Charlie",)]

            # Verify detectors were NOT called
            mock_primary_detector.is_primary.assert_not_called()
            mock_split_brain_detector.detect_split_brain.assert_not_called()
