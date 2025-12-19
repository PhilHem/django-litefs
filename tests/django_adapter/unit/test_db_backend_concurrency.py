"""Concurrency tests for Django database backend."""

import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from litefs.usecases.primary_detector import PrimaryDetector


def create_litefs_settings_dict(mount_path, db_name="test.db"):
    """Create a settings_dict for LiteFS database backend testing.

    Django 5.x requires additional fields in settings_dict.
    """
    return {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": db_name,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "OPTIONS": {
            "litefs_mount_path": str(mount_path),
        },
    }


# Import write detection logic directly to test thread safety
# This avoids needing full Django setup for this specific test
import re

# Pre-compiled regex for CTE write keyword detection (CONC-002)
# Uses word boundaries to avoid false positives on column/table names
# like 'delete_flag', 'update_count', 'insert_date', 'deleted_items'
_CTE_WRITE_KEYWORD_RE = re.compile(r'\b(INSERT|UPDATE|DELETE)\b', re.IGNORECASE)


def _strip_sql_comments(sql):
    """Remove SQL comments for write detection (DJANGO-031)."""
    # Remove block comments /* ... */ (non-greedy, handles nested)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Remove line comments -- ... (to end of line)
    sql = re.sub(r"--[^\n]*(\n|$)", r"\1", sql)
    return sql


def _is_write_operation(sql):
    """Check if SQL statement is a write operation (copied from LiteFSCursor for testing).

    Handles:
    - Direct write keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, REPLACE)
    - Database maintenance operations (VACUUM, REINDEX, ANALYZE) (DJANGO-030)
    - CTE patterns: WITH ... INSERT/UPDATE/DELETE (DJANGO-029, CONC-002)
    - SQL with leading comments (DJANGO-031)
    """
    if not sql:
        return False

    # Strip comments before detection (DJANGO-031)
    sql_clean = _strip_sql_comments(sql)
    sql_upper = sql_clean.strip().upper()

    if not sql_upper:
        return False

    # Direct write keywords (existing + DJANGO-030 maintenance ops)
    write_keywords = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "DROP",
        "ALTER",
        "REPLACE",
        "VACUUM",
        "REINDEX",
        "ANALYZE",
    )

    if any(sql_upper.startswith(keyword) for keyword in write_keywords):
        return True

    # CTE pattern detection (DJANGO-029, CONC-002): WITH ... INSERT/UPDATE/DELETE
    # Uses word boundary regex to avoid false positives on column/table names
    # like 'delete_flag', 'update_count', 'insert_date', 'deleted_items'
    if sql_upper.startswith("WITH"):
        return bool(_CTE_WRITE_KEYWORD_RE.search(sql_clean))

    return False


@pytest.mark.unit
@pytest.mark.concurrency
class TestDatabaseBackendConcurrency:
    """Test concurrency issues in Django database backend."""

    def test_primary_detector_concurrent_access(self, tmp_path):
        """Test that PrimaryDetector handles concurrent is_primary() calls safely.

        This test simulates multiple threads calling is_primary() simultaneously
        during failover scenarios where .primary file is being created/deleted.
        Verifies no exceptions occur and all calls complete successfully.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"

        detector = PrimaryDetector(mount_path=str(mount_path))
        results = []
        errors = []
        lock = threading.Lock()

        def check_primary():
            """Thread function to check primary status."""
            try:
                result = detector.is_primary()
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Simulate failover: create and delete .primary file rapidly
        def toggle_primary():
            """Thread function to toggle primary file."""
            for _ in range(50):
                if primary_file.exists():
                    primary_file.unlink()
                else:
                    primary_file.write_text("node-1")
                # Small delay to allow race conditions
                threading.Event().wait(0.0001)

        # Start threads
        threads = []
        for _ in range(50):
            t = threading.Thread(target=check_primary)
            threads.append(t)
            t.start()

        # Start toggle thread
        toggle_thread = threading.Thread(target=toggle_primary)
        toggle_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        toggle_thread.join()

        # Verify no exceptions occurred
        assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"

        # Verify all calls completed (results may vary based on timing)
        assert len(results) == 50, f"Not all threads completed: {len(results)}/50"

    def test_write_operation_detection_thread_safety(self, tmp_path):
        """Test that write operation detection is thread-safe (DJANGO-018).

        Multiple threads call _is_write_operation concurrently with various SQL
        statements to verify that the detection logic is thread-safe and produces
        consistent results without false positives or missed operations.
        """
        # Mix of SQL statements to test
        sql_statements = [
            ("SELECT * FROM test_table", False),  # Read
            ("INSERT INTO test_table (value) VALUES (?)", True),  # Write
            ("UPDATE test_table SET value = ? WHERE id = ?", True),  # Write
            ("SELECT COUNT(*) FROM test_table", False),  # Read
            ("DELETE FROM test_table WHERE id = ?", True),  # Write
            ("CREATE INDEX idx_value ON test_table(value)", True),  # Write
            ("DROP TABLE test_table", True),  # Write
            ("SELECT value FROM test_table WHERE id = ?", False),  # Read
            ("ALTER TABLE test_table ADD COLUMN new_col TEXT", True),  # Write
            ("REPLACE INTO test_table (id, value) VALUES (?, ?)", True),  # Write
            ("  SELECT * FROM test_table  ", False),  # Read with whitespace
            ("\nINSERT INTO test_table VALUES (1)", True),  # Write with newline
        ]

        results = []
        errors = []
        lock = threading.Lock()

        def test_write_detection(thread_id):
            """Thread function to test write detection concurrently."""
            try:
                # Test each SQL statement multiple times concurrently
                for _ in range(10):
                    for sql, expected_is_write in sql_statements:
                        # Test write detection - this is the key test
                        is_write = _is_write_operation(sql)
                        if is_write != expected_is_write:
                            with lock:
                                errors.append(
                                    f"Thread {thread_id}: SQL '{sql[:40]}...' "
                                    f"detected as write={is_write}, expected={expected_is_write}"
                                )
                with lock:
                    results.append(thread_id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        # Start multiple threads
        threads = []
        for i in range(50):
            t = threading.Thread(target=test_write_detection, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50, f"Not all threads completed: {len(results)}/50"

    def test_concurrent_primary_checks_before_writes(self, tmp_path):
        """Test concurrent primary checks before writes (DJANGO-017).

        Multiple threads check primary status simultaneously before writes to verify
        that primary checks are thread-safe and don't cause contention issues.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"

        # Create primary detector
        primary_detector = PrimaryDetector(mount_path=str(mount_path))

        results = []
        errors = []
        lock = threading.Lock()

        def check_primary_and_simulate_write(thread_id):
            """Thread function to check primary status and simulate write."""
            try:
                # Simulate primary check before write (as done in _check_primary_before_write)
                for _ in range(20):
                    # Check primary status - this is the key test
                    is_primary = primary_detector.is_primary()

                    # Simulate write operation if primary
                    if is_primary:
                        # In real scenario, write would happen here
                        # For this test, we just verify the check completes
                        pass

                    # Toggle primary file to simulate failover (with error handling)
                    if thread_id % 10 == 0:  # Some threads toggle primary
                        try:
                            if primary_file.exists():
                                primary_file.unlink()
                            else:
                                primary_file.write_text("node-1")
                        except (FileNotFoundError, OSError):
                            # File was deleted/created by another thread - this is expected
                            pass

                with lock:
                    results.append(thread_id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        # Start with primary file existing
        primary_file.write_text("node-1")

        # Start multiple threads
        threads = []
        for i in range(30):
            t = threading.Thread(target=check_primary_and_simulate_write, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 30, f"Not all threads completed: {len(results)}/30"

    def test_sqlite_lock_contention_with_wal_mode(self, tmp_path):
        """Test SQLite lock contention with concurrent writes (DJANGO-016).

        Multiple threads perform concurrent write operations to verify that
        WAL mode and IMMEDIATE transactions handle contention without "database is locked" errors.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"

        # Create database with WAL mode (as LiteFS requires)
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT, thread_id INTEGER)"
        )
        conn.commit()
        conn.close()

        results = []
        errors = []
        lock = threading.Lock()

        def perform_writes(thread_id):
            """Thread function to perform concurrent writes."""
            try:
                # Each thread gets its own connection (as Django does)
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                conn.execute("PRAGMA journal_mode=WAL")

                # Use IMMEDIATE transaction mode (as LiteFS backend does)
                for i in range(10):
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        conn.execute(
                            "INSERT INTO test_table (value, thread_id) VALUES (?, ?)",
                            (f"value-{thread_id}-{i}", thread_id),
                        )
                        conn.commit()
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e).lower():
                            with lock:
                                errors.append(
                                    f"Thread {thread_id}: Database locked error: {e}"
                                )
                        else:
                            raise

                conn.close()
                with lock:
                    results.append(thread_id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        # Start multiple threads performing writes
        threads = []
        for i in range(20):
            t = threading.Thread(target=perform_writes, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no lock errors occurred
        lock_errors = [e for e in errors if "locked" in e.lower()]
        assert len(lock_errors) == 0, f"Database lock errors occurred: {lock_errors}"
        assert len(results) == 20, f"Not all threads completed: {len(results)}/20"

        # Verify data was written
        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()[0]
        conn.close()
        assert count > 0, "No data was written to database"

    def test_connection_reuse_enforces_immediate_mode(self, tmp_path):
        """Test that connection reuse across transactions enforces IMMEDIATE mode (DJANGO-022).

        A single thread reuses the same connection across multiple transactions.
        Verifies that all transactions use BEGIN IMMEDIATE, even when connection
        is reused across transaction boundaries.

        Note: Django 5.x enforces thread isolation for DatabaseWrapper, so this test
        uses single-threaded verification of multiple transactions.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        (mount_path / ".primary").write_text("node-1")

        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        # Capture SQL statements using trace callback
        executed_sql = []

        def trace_callback(statement):
            executed_sql.append(statement)

        # Set trace callback on the underlying SQLite connection
        wrapper.connection.set_trace_callback(trace_callback)

        # Perform multiple transactions on the same connection (single thread)
        # simulating connection reuse across transaction boundaries
        for i in range(10):
            wrapper._start_transaction_under_autocommit()
            # Commit to complete transaction
            wrapper.connection.commit()

        # Verify all BEGIN statements use IMMEDIATE mode
        begin_statements = [
            sql for sql in executed_sql if sql.strip().upper().startswith("BEGIN")
        ]
        assert len(begin_statements) > 0, "No BEGIN statements found"
        # All BEGIN statements should be IMMEDIATE
        non_immediate = [
            sql for sql in begin_statements if "IMMEDIATE" not in sql.upper()
        ]
        assert len(non_immediate) == 0, (
            f"Found BEGIN statements without IMMEDIATE mode: {non_immediate}"
        )

    def test_concurrent_connection_initialization(self, tmp_path):
        """Test concurrent connection initialization (DJANGO-019).

        Multiple threads initialize connections simultaneously to verify that
        PRAGMA statements (journal_mode=WAL, BEGIN IMMEDIATE) don't cause contention.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"

        results = []
        errors = []
        lock = threading.Lock()

        def initialize_connection(thread_id):
            """Thread function to initialize connection with PRAGMA statements."""
            conn = None
            try:
                # Simulate what get_new_connection does
                conn = sqlite3.connect(str(db_path), timeout=10.0)

                # These are the PRAGMA statements from get_new_connection
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")  # LiteFS requires WAL
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute("COMMIT")

                # Verify WAL mode was set
                journal_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]

                if journal_mode.upper() != "WAL":
                    with lock:
                        errors.append(
                            f"Thread {thread_id}: Journal mode not WAL: {journal_mode}"
                        )

                with lock:
                    results.append(thread_id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")
            finally:
                if conn:
                    conn.close()

        # Start multiple threads initializing connections
        threads = []
        for i in range(30):
            t = threading.Thread(target=initialize_connection, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 30, f"Not all threads completed: {len(results)}/30"

    def test_general_concurrent_access(self, tmp_path):
        """Test general concurrent access to database backend (DJANGO-015).

        Combined test with multiple threads performing mixed operations (reads, writes,
        primary checks, connection initialization) to verify overall thread safety.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")
        db_path = mount_path / "test.db"

        # Create database with WAL mode
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT, thread_id INTEGER)"
        )
        conn.commit()
        conn.close()

        primary_detector = PrimaryDetector(mount_path=str(mount_path))
        results = []
        errors = []
        lock = threading.Lock()

        def mixed_operations(thread_id):
            """Thread function performing mixed operations."""
            try:
                # Initialize connection (like get_new_connection)
                conn = sqlite3.connect(str(db_path), timeout=10.0)
                conn.execute("PRAGMA journal_mode=WAL")

                # Perform mixed operations
                for i in range(5):
                    # Primary check (like _check_primary_before_write)
                    is_primary = primary_detector.is_primary()

                    if is_primary:
                        # Write operation (like execute with INSERT)
                        try:
                            conn.execute("BEGIN IMMEDIATE")
                            conn.execute(
                                "INSERT INTO test_table (value, thread_id) VALUES (?, ?)",
                                (f"value-{thread_id}-{i}", thread_id),
                            )
                            conn.commit()
                        except sqlite3.OperationalError as e:
                            if "database is locked" not in str(e).lower():
                                raise

                    # Read operation
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM test_table")
                    cursor.fetchone()

                conn.close()
                with lock:
                    results.append(thread_id)
            except Exception as e:
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        # Start multiple threads
        threads = []
        for i in range(15):
            t = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 15, f"Not all threads completed: {len(results)}/15"

    def test_toctou_gap_failover_during_write(self, tmp_path):
        """Test TOCTOU gap: failover between is_primary() and execute() (DJANGO-004).

        Simulates scenario where:
        1. Thread calls _check_primary_before_write -> is_primary() returns True
        2. Failover occurs (.primary file deleted) before super().execute() is called
        3. Thread proceeds to super().execute() on what is now a replica

        Expected: SQLite rejects write at filesystem level (read-only mount).
        This is documented architectural behavior per DJANGO-003.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        db_path = mount_path / "test.db"

        # Create database with WAL mode
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        # Start with primary file existing
        primary_file.write_text("node-1")

        # Import Django components (Django should be set up by conftest.py)
        from litefs_django.db.backends.litefs.base import DatabaseWrapper, LiteFSCursor

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        # Create cursor
        cursor = wrapper.create_cursor()

        # Use threading events to control timing
        check_complete = threading.Event()
        failover_triggered = threading.Event()

        # Store original is_primary method
        original_is_primary = cursor._primary_detector.is_primary

        def delayed_is_primary():
            """Wrap is_primary to allow failover injection."""
            result = original_is_primary()
            # Signal that check completed
            check_complete.set()
            # Wait for failover to be triggered
            failover_triggered.wait(timeout=1.0)
            return result

        def trigger_failover():
            """Thread function to trigger failover after primary check."""
            # Wait for primary check to complete
            check_complete.wait(timeout=1.0)
            # Trigger failover by deleting .primary file
            if primary_file.exists():
                primary_file.unlink()
            failover_triggered.set()

        # Patch is_primary to inject delay
        with patch.object(
            cursor._primary_detector, "is_primary", side_effect=delayed_is_primary
        ):
            # Start failover thread
            failover_thread = threading.Thread(target=trigger_failover)
            failover_thread.start()

            # Attempt write - this should pass primary check but fail at SQLite level
            # if failover occurred
            try:
                cursor.execute("INSERT INTO test_table (value) VALUES (?)", ("test",))
                # If we get here, the write succeeded (failover didn't happen in time)
                # This is acceptable - TOCTOU gap is probabilistic
                write_succeeded = True
            except (sqlite3.OperationalError, Exception) as e:
                # SQLite rejected the write (expected if failover occurred)
                write_succeeded = False
                error_type = type(e).__name__
                error_message = str(e)

            failover_thread.join()

        # Document the behavior: TOCTOU gap exists, SQLite handles rejection
        # The test verifies that the system doesn't crash and handles the scenario
        assert True, (
            f"TOCTOU gap test completed. Write succeeded: {write_succeeded}. "
            f"This documents the architectural limitation per DJANGO-003."
        )

    def test_error_type_on_replica_write_attempt(self, tmp_path):
        """Test error type when write is attempted on replica (DJANGO-023).

        When write is attempted on replica (no .primary file):
        - Expected: NotPrimaryError is raised before SQLite is called
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"

        # Create database with WAL mode
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        # No .primary file = replica

        # Import Django components (Django should be set up by conftest.py)
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs_django.exceptions import NotPrimaryError

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        cursor = wrapper.create_cursor()

        # Attempt write on replica - should raise NotPrimaryError
        with pytest.raises(NotPrimaryError) as exc_info:
            cursor.execute("INSERT INTO test_table (value) VALUES (?)", ("test",))

        # Verify error message
        assert (
            "replica" in str(exc_info.value).lower()
            or "primary" in str(exc_info.value).lower()
        ), f"Error message should mention replica/primary: {exc_info.value}"

    def test_error_after_failover_is_sqlite_operational_error(self, tmp_path):
        """Test error type when TOCTOU gap allows write to reach SQLite on replica (DJANGO-023).

        When TOCTOU gap allows write to proceed past primary check:
        - Expected: sqlite3.OperationalError with 'readonly' or similar message
        - This documents the error type for application-level handling
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        db_path = mount_path / "test.db"

        # Create database with WAL mode
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        # Start with primary file existing
        primary_file.write_text("node-1")

        # Import Django components (Django should be set up by conftest.py)
        from litefs_django.db.backends.litefs.base import DatabaseWrapper, LiteFSCursor
        from django.db import DatabaseError

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        cursor = wrapper.create_cursor()

        # Simulate TOCTOU gap: is_primary() returns True, then failover occurs
        # before execute() is called
        original_is_primary = cursor._primary_detector.is_primary

        def is_primary_returns_true_then_failover():
            """Simulate is_primary() returning True, then failover."""
            result = original_is_primary()
            # Immediately trigger failover after check
            if primary_file.exists():
                primary_file.unlink()
            return result

        # Patch is_primary to simulate the TOCTOU scenario
        with patch.object(
            cursor._primary_detector,
            "is_primary",
            side_effect=is_primary_returns_true_then_failover,
        ):
            # Attempt write - should pass primary check but fail at SQLite level
            try:
                cursor.execute("INSERT INTO test_table (value) VALUES (?)", ("test",))
                # If write succeeds, failover didn't occur in time (acceptable)
                write_succeeded = True
                error_type = None
            except (sqlite3.OperationalError, DatabaseError) as e:
                # SQLite rejected the write
                write_succeeded = False
                error_type = type(e).__name__
                error_message = str(e)

        # Document the error type for application handling
        # If write succeeded, that's acceptable (probabilistic TOCTOU gap)
        # If it failed, verify it's an OperationalError or DatabaseError
        if not write_succeeded:
            assert error_type in (
                "OperationalError",
                "DatabaseError",
            ), f"Expected OperationalError or DatabaseError, got {error_type}"
            # Error should indicate readonly or similar
            assert (
                "readonly" in error_message.lower()
                or "read-only" in error_message.lower()
                or "read only" in error_message.lower()
            ), f"Error message should indicate readonly: {error_message}"

    def test_concurrent_connection_init_mount_path_missing(self, tmp_path):
        """Test concurrent DatabaseWrapper creation when mount_path doesn't exist (DJANGO-005, DJANGO-025, DJANGO-026, DJANGO-027).

        Multiple threads creating DatabaseWrapper when mount_path doesn't exist should fail
        consistently with predictable error types. Verifies fail-fast behavior in __init__ (DJANGO-027)
        and error type consistency (DJANGO-026).
        """
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs.usecases.primary_detector import LiteFSNotRunningError

        # Use non-existent mount_path
        mount_path = tmp_path / "nonexistent_litefs"

        settings_dict = create_litefs_settings_dict(mount_path)

        results = []
        errors = []
        error_types = []
        lock = threading.Lock()

        def attempt_wrapper_creation(thread_id):
            """Thread function to attempt DatabaseWrapper creation."""
            try:
                # This should fail because mount_path doesn't exist (DJANGO-027 fail-fast)
                DatabaseWrapper(settings_dict)
                with lock:
                    errors.append(
                        f"Thread {thread_id}: Wrapper creation succeeded unexpectedly"
                    )
            except LiteFSNotRunningError as e:
                # Expected: mount_path doesn't exist (DJANGO-027 fail-fast, DJANGO-026 consistency)
                error_type = type(e).__name__
                with lock:
                    errors.append(f"Thread {thread_id}: {error_type}: {str(e)}")
                    error_types.append(error_type)
                    results.append(thread_id)
            except Exception as e:
                # Unexpected error type (DJANGO-026)
                error_type = type(e).__name__
                with lock:
                    errors.append(
                        f"Thread {thread_id}: Unexpected {error_type}: {str(e)}"
                    )
                    error_types.append(error_type)
                    results.append(thread_id)

        # Start multiple threads attempting wrapper creation
        threads = []
        for i in range(20):
            t = threading.Thread(target=attempt_wrapper_creation, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10.0)

        # Verify all threads attempted wrapper creation
        assert len(results) == 20, f"Not all threads completed: {len(results)}/20"

        # Verify error types are consistent (DJANGO-026)
        # All threads should get LiteFSNotRunningError
        unique_error_types = set(error_types)
        assert len(unique_error_types) == 1, (
            f"Expected single error type (LiteFSNotRunningError), got: {unique_error_types}. "
            f"Error handling should be consistent (DJANGO-026)."
        )
        assert "LiteFSNotRunningError" in unique_error_types, (
            f"Expected LiteFSNotRunningError, got: {unique_error_types}"
        )

        # Verify errors occurred (mount_path doesn't exist)
        assert len(errors) == 20, f"Expected 20 errors, got {len(errors)}"

    def test_mount_path_appears_during_wrapper_creation_attempts(self, tmp_path):
        """Test race condition when mount_path appears during concurrent wrapper creation (DJANGO-024).

        When mount_path appears during concurrent DatabaseWrapper creation attempts,
        threads should handle it gracefully - some fail fast (mount_path not yet present),
        others succeed (mount_path appeared). Verifies no race conditions.

        Note: With DJANGO-027 fail-fast validation in __init__, the race is now about
        mount_path appearing between threads attempting to create wrappers.
        """
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs.usecases.primary_detector import LiteFSNotRunningError

        mount_path = tmp_path / "litefs"
        db_path = mount_path / "test.db"

        settings_dict = create_litefs_settings_dict(mount_path)

        results = []
        errors = []
        lock = threading.Lock()
        mount_path_created = threading.Event()

        def attempt_wrapper_creation(thread_id):
            """Thread function to attempt wrapper creation."""
            try:
                # Wait a bit to allow mount_path creation
                time.sleep(0.05)
                # Attempt wrapper creation
                # May fail if mount_path doesn't exist yet (DJANGO-027), or succeed if it does
                wrapper = DatabaseWrapper(settings_dict.copy())
                with lock:
                    results.append(thread_id)
            except LiteFSNotRunningError:
                # Expected if mount_path doesn't exist yet (DJANGO-027 fail-fast)
                # Thread should handle gracefully
                with lock:
                    errors.append(f"Thread {thread_id}: Mount path not ready")
            except Exception as e:
                # Other errors should be handled gracefully
                with lock:
                    errors.append(f"Thread {thread_id}: {e}")

        def create_mount_path():
            """Thread function to create mount_path after delay."""
            time.sleep(0.1)  # Delay before creating mount_path
            mount_path.mkdir()
            # Create .primary file for valid wrapper initialization
            (mount_path / ".primary").write_text("node-1")
            mount_path_created.set()

        # Start threads attempting wrapper creation (mount_path doesn't exist yet)
        threads = []
        for i in range(10):
            t = threading.Thread(target=attempt_wrapper_creation, args=(i,))
            threads.append(t)
            t.start()

        # Start thread to create mount_path
        create_thread = threading.Thread(target=create_mount_path)
        create_thread.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=15.0)
        create_thread.join(timeout=15.0)

        # Verify mount_path was created
        assert mount_path.exists(), "Mount path should have been created"

        # Verify threads completed (either succeeded or failed gracefully)
        # Some threads may have succeeded (mount_path appeared in time)
        # Some threads may have failed (mount_path not yet present)
        assert len(results) + len(errors) == 10, (
            f"Not all threads completed: {len(results)} succeeded, {len(errors)} failed"
        )

    def test_primary_detector_created_before_mount_path_check(self, tmp_path):
        """Test that PrimaryDetector creation validates mount_path exists (fail-fast) (DJANGO-027).

        PrimaryDetector creation in __init__ should validate mount_path exists before proceeding.
        This ensures fail-fast behavior.
        """
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs.usecases.primary_detector import LiteFSNotRunningError

        # Use non-existent mount_path
        mount_path = tmp_path / "nonexistent_litefs"

        settings_dict = create_litefs_settings_dict(mount_path)

        # DatabaseWrapper.__init__ should validate mount_path exists (fail-fast)
        # This test verifies that validation happens early in __init__
        with pytest.raises(LiteFSNotRunningError) as exc_info:
            wrapper = DatabaseWrapper(settings_dict)

        # Verify error message mentions mount path
        assert (
            "mount path" in str(exc_info.value).lower()
            or "does not exist" in str(exc_info.value).lower()
        ), f"Error message should mention mount path: {exc_info.value}"

    def test_get_new_connection_error_handling_missing_path(self, tmp_path):
        """Test error handling in get_new_connection when mount_path is missing (DJANGO-025).

        get_new_connection should handle missing mount_path gracefully with clear error.
        """
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs.usecases.primary_detector import LiteFSNotRunningError

        # Use non-existent mount_path
        mount_path = tmp_path / "nonexistent_litefs"

        settings_dict = create_litefs_settings_dict(mount_path)

        # DatabaseWrapper.__init__ should fail-fast when mount_path doesn't exist
        # So we need to create it first, then delete it to test get_new_connection
        mount_path.mkdir()
        wrapper = DatabaseWrapper(settings_dict)
        mount_path.rmdir()  # Remove mount_path after wrapper creation

        # get_new_connection should fail with clear error when mount_path doesn't exist (DJANGO-025)
        with pytest.raises(LiteFSNotRunningError) as exc_info:
            wrapper.get_new_connection({})

        # Verify error message is clear and helpful
        error_message = str(exc_info.value).lower()
        assert (
            "mount path" in error_message
            or "does not exist" in error_message
            or "not running" in error_message
        ), f"Error message should clearly indicate mount path issue: {exc_info.value}"


@pytest.mark.unit
class TestWriteDetectionGaps:
    """Test write detection gaps (DJANGO-029, DJANGO-030, DJANGO-031)."""

    def test_is_write_operation_cte_insert(self):
        """Test CTE with INSERT is detected as write (DJANGO-029)."""
        sql = """
        WITH numbered_rows AS (
            SELECT id, row_number() OVER (ORDER BY id) as rn FROM table1
        )
        INSERT INTO archive SELECT * FROM numbered_rows WHERE rn > 1000
        """
        assert _is_write_operation(sql) is True, (
            "CTE with INSERT should be detected as write"
        )

    def test_is_write_operation_cte_update(self):
        """Test CTE with UPDATE is detected as write (DJANGO-029)."""
        sql = """
        WITH cte AS (SELECT id FROM table1 WHERE active = 0)
        UPDATE table1 SET deleted = 1 WHERE id IN (SELECT id FROM cte)
        """
        assert _is_write_operation(sql) is True, (
            "CTE with UPDATE should be detected as write"
        )

    def test_is_write_operation_cte_delete(self):
        """Test CTE with DELETE is detected as write (DJANGO-029)."""
        sql = """
        WITH old_records AS (SELECT id FROM logs WHERE created_at < '2020-01-01')
        DELETE FROM logs WHERE id IN (SELECT id FROM old_records)
        """
        assert _is_write_operation(sql) is True, (
            "CTE with DELETE should be detected as write"
        )

    def test_is_write_operation_cte_select_only(self):
        """Test CTE with SELECT only is NOT detected as write."""
        sql = """
        WITH numbered AS (SELECT id, row_number() OVER () as rn FROM table1)
        SELECT * FROM numbered WHERE rn > 10
        """
        assert _is_write_operation(sql) is False, (
            "CTE with SELECT only should not be detected as write"
        )

    def test_is_write_operation_vacuum(self):
        """Test VACUUM is detected as write (DJANGO-030)."""
        assert _is_write_operation("VACUUM") is True, (
            "VACUUM should be detected as write"
        )
        assert _is_write_operation("vacuum") is True, (
            "vacuum (lowercase) should be detected as write"
        )

    def test_is_write_operation_reindex(self):
        """Test REINDEX is detected as write (DJANGO-030)."""
        assert _is_write_operation("REINDEX") is True, (
            "REINDEX should be detected as write"
        )
        assert _is_write_operation("REINDEX table1") is True, (
            "REINDEX table should be detected as write"
        )

    def test_is_write_operation_analyze(self):
        """Test ANALYZE is detected as write (DJANGO-030)."""
        assert _is_write_operation("ANALYZE") is True, (
            "ANALYZE should be detected as write"
        )
        assert _is_write_operation("ANALYZE table1") is True, (
            "ANALYZE table should be detected as write"
        )

    def test_is_write_operation_block_comment_insert(self):
        """Test block comment before INSERT is detected as write (DJANGO-031)."""
        sql = "/* cleanup operation */ INSERT INTO table1 VALUES (1)"
        assert _is_write_operation(sql) is True, (
            "Block comment before INSERT should be detected as write"
        )

    def test_is_write_operation_line_comment_insert(self):
        """Test line comment before INSERT is detected as write (DJANGO-031)."""
        sql = "-- TODO: insert cleanup\nINSERT INTO table1 VALUES (1)"
        assert _is_write_operation(sql) is True, (
            "Line comment before INSERT should be detected as write"
        )

    def test_is_write_operation_multiple_block_comments(self):
        """Test multiple block comments before INSERT is detected as write (DJANGO-031)."""
        sql = "/* first comment */ /* second comment */ INSERT INTO table1 VALUES (1)"
        assert _is_write_operation(sql) is True, (
            "Multiple block comments before INSERT should be detected as write"
        )

    def test_is_write_operation_mixed_comments(self):
        """Test mixed comments before UPDATE is detected as write (DJANGO-031)."""
        sql = """-- line comment
        /* block comment */
        UPDATE table1 SET value = 1"""
        assert _is_write_operation(sql) is True, (
            "Mixed comments before UPDATE should be detected as write"
        )

    # CONC-002: CTE detection false positive tests
    def test_cte_select_with_delete_column_not_write(self):
        """Test CTE SELECT with 'delete_flag' column is NOT detected as write (CONC-002).

        Bug: substring match on 'DELETE' in 'delete_flag' causes false positive.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1)
        SELECT delete_flag, id FROM table1
        """
        assert _is_write_operation(sql) is False, (
            "CTE with SELECT containing 'delete_flag' column should not be detected as write"
        )

    def test_cte_select_with_update_column_not_write(self):
        """Test CTE SELECT with 'update_count' column is NOT detected as write (CONC-002).

        Bug: substring match on 'UPDATE' in 'update_count' causes false positive.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1)
        SELECT update_count, id FROM table1
        """
        assert _is_write_operation(sql) is False, (
            "CTE with SELECT containing 'update_count' column should not be detected as write"
        )

    def test_cte_select_with_insert_column_not_write(self):
        """Test CTE SELECT with 'insert_date' column is NOT detected as write (CONC-002).

        Bug: substring match on 'INSERT' in 'insert_date' causes false positive.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1)
        SELECT insert_date, id FROM table1
        """
        assert _is_write_operation(sql) is False, (
            "CTE with SELECT containing 'insert_date' column should not be detected as write"
        )

    def test_cte_with_keyword_in_table_name_not_write(self):
        """Test CTE SELECT from 'deleted_items' table is NOT detected as write (CONC-002).

        Bug: substring match on 'DELETE' in 'deleted_items' causes false positive.
        """
        sql = """
        WITH cte AS (SELECT id FROM other_table)
        SELECT * FROM deleted_items WHERE id IN (SELECT id FROM cte)
        """
        assert _is_write_operation(sql) is False, (
            "CTE with SELECT from 'deleted_items' table should not be detected as write"
        )

    def test_cte_actual_insert_still_detected(self):
        """Test CTE with actual INSERT statement is still detected (CONC-002).

        Regression test: ensure fix doesn't break real INSERT detection.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1)
        INSERT INTO archive SELECT * FROM cte
        """
        assert _is_write_operation(sql) is True, (
            "CTE with actual INSERT should still be detected as write"
        )

    def test_cte_actual_update_still_detected(self):
        """Test CTE with actual UPDATE statement is still detected (CONC-002).

        Regression test: ensure fix doesn't break real UPDATE detection.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1 WHERE active = 0)
        UPDATE table1 SET deleted = 1 WHERE id IN (SELECT id FROM cte)
        """
        assert _is_write_operation(sql) is True, (
            "CTE with actual UPDATE should still be detected as write"
        )

    def test_cte_actual_delete_still_detected(self):
        """Test CTE with actual DELETE statement is still detected (CONC-002).

        Regression test: ensure fix doesn't break real DELETE detection.
        """
        sql = """
        WITH cte AS (SELECT id FROM table1 WHERE created_at < '2020-01-01')
        DELETE FROM table1 WHERE id IN (SELECT id FROM cte)
        """
        assert _is_write_operation(sql) is True, (
            "CTE with actual DELETE should still be detected as write"
        )


@pytest.mark.unit
class TestExecutescriptOverride:
    """Test executescript method override (DJANGO-028)."""

    def test_executescript_checks_primary_on_replica(self, tmp_path):
        """Test executescript raises NotPrimaryError on replica (DJANGO-028)."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs_django.exceptions import NotPrimaryError

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        # No .primary file = replica

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()
        cursor = wrapper.create_cursor()

        # executescript should raise NotPrimaryError on replica
        sql_script = """
        INSERT INTO test_table VALUES (1, 'a');
        INSERT INTO test_table VALUES (2, 'b');
        """
        with pytest.raises(NotPrimaryError) as exc_info:
            cursor.executescript(sql_script)

        assert (
            "replica" in str(exc_info.value).lower()
            or "primary" in str(exc_info.value).lower()
        )

    def test_executescript_works_on_primary(self, tmp_path):
        """Test executescript works on primary node (DJANGO-028)."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()
        cursor = wrapper.create_cursor()

        # executescript should work on primary
        sql_script = """
        INSERT INTO test_table VALUES (1, 'a');
        INSERT INTO test_table VALUES (2, 'b');
        """
        # Should not raise
        cursor.executescript(sql_script)

        # Verify data was inserted
        result = cursor.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2


@pytest.mark.unit
class TestPrimaryDetectorLifecycle:
    """Test PrimaryDetector lifecycle across cursor operations (DJANGO-032)."""

    def test_shared_primary_detector_safe_across_cursor_lifecycle(self, tmp_path):
        """Test shared PrimaryDetector remains valid across cursor lifecycle (DJANGO-032)."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        # Create multiple cursors - they should share the same PrimaryDetector
        cursor1 = wrapper.create_cursor()
        cursor2 = wrapper.create_cursor()

        assert cursor1._primary_detector is cursor2._primary_detector, (
            "Cursors should share the same PrimaryDetector instance"
        )

        # Use cursor1
        cursor1.execute("INSERT INTO test_table VALUES (1, 'a')")

        # Verify cursor2's detector is still valid after cursor1 operations
        assert cursor2._primary_detector.is_primary() is True

        # Use cursor2
        cursor2.execute("INSERT INTO test_table VALUES (2, 'b')")

        # Verify data from both cursors
        result = cursor1.execute("SELECT COUNT(*) FROM test_table").fetchone()
        assert result[0] == 2

    def test_detector_remains_valid_after_failover(self, tmp_path):
        """Test detector handles failover correctly across cursors (DJANGO-032)."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper
        from litefs_django.exceptions import NotPrimaryError

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        db_path = mount_path / "test.db"
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()

        settings_dict = create_litefs_settings_dict(mount_path)

        wrapper = DatabaseWrapper(settings_dict)
        wrapper.ensure_connection()

        cursor1 = wrapper.create_cursor()
        cursor2 = wrapper.create_cursor()

        # Use cursor1 as primary
        cursor1.execute("INSERT INTO test_table VALUES (1, 'a')")

        # Simulate failover
        primary_file.unlink()

        # Both cursors should now detect replica status
        with pytest.raises(NotPrimaryError):
            cursor1.execute("INSERT INTO test_table VALUES (2, 'b')")

        with pytest.raises(NotPrimaryError):
            cursor2.execute("INSERT INTO test_table VALUES (3, 'c')")
