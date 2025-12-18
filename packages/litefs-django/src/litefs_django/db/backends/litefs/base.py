"""LiteFS database backend base implementation."""

from pathlib import Path

from django.db.backends.sqlite3.base import (
    DatabaseWrapper as SQLite3DatabaseWrapper,
    Cursor as SQLite3Cursor,
)

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs_django.exceptions import NotPrimaryError


class LiteFSCursor(SQLite3Cursor):
    """Cursor with primary detection for write operations."""

    def __init__(self, connection, primary_detector):
        """Initialize LiteFS cursor.

        Args:
            connection: Database connection
            primary_detector: PrimaryDetector use case instance
        """
        super().__init__(connection)
        self._primary_detector = primary_detector

    def _check_primary_before_write(self, sql):
        """Check if this node is primary before write operations.

        Args:
            sql: SQL statement to check

        Raises:
            NotPrimaryError: If this node is not primary (replica)
        """
        if self._is_write_operation(sql):
            try:
                if not self._primary_detector.is_primary():
                    raise NotPrimaryError(
                        "Write operation attempted on replica node. "
                        "Only the primary node can perform writes."
                    )
            except NotPrimaryError:
                raise
            except Exception:
                # Re-raise other exceptions (e.g., LiteFSNotRunningError)
                raise

    def _is_write_operation(self, sql):
        """Check if SQL statement is a write operation.

        Args:
            sql: SQL statement string

        Returns:
            True if statement is a write operation (INSERT, UPDATE, DELETE, etc.)
        """
        if not sql:
            return False
        sql_upper = sql.strip().upper()
        write_keywords = (
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "DROP",
            "ALTER",
            "REPLACE",
        )
        return any(sql_upper.startswith(keyword) for keyword in write_keywords)

    def execute(self, sql, params=None):
        """Execute SQL statement with primary check for write operations.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Query result

        Raises:
            NotPrimaryError: If write attempted on replica
        """
        self._check_primary_before_write(sql)
        return super().execute(sql, params)

    def executemany(self, sql, param_list):
        """Execute SQL statement multiple times with primary check.

        Args:
            sql: SQL statement
            param_list: List of parameter tuples

        Returns:
            Query result

        Raises:
            NotPrimaryError: If write attempted on replica
        """
        self._check_primary_before_write(sql)
        return super().executemany(sql, param_list)


class DatabaseWrapper(SQLite3DatabaseWrapper):
    """Django database backend for LiteFS SQLite replication.

    Subclasses SQLite3 backend and adds LiteFS-specific functionality:
    - Uses LiteFS mount path for database location
    - Enforces IMMEDIATE transaction mode
    - Delegates primary detection to PrimaryDetector use case
    - Checks primary status before write operations

    Note: There is a TOCTOU (time-of-check-time-of-use) race condition where
    primary status can change between check and write. This is an architectural
    limitation of LiteFS's single-writer model. Writes may fail if failover
    occurs during a transaction.
    """

    def __init__(self, settings_dict, alias="default", allow_thread_sharing=None):
        """Initialize LiteFS database backend.

        Args:
            settings_dict: Django database settings dict
            alias: Database alias
            allow_thread_sharing: Thread sharing flag (deprecated in Django 5.x)
        """
        # Extract LiteFS mount path from OPTIONS
        options = settings_dict.get("OPTIONS", {})
        mount_path = options.get("litefs_mount_path")

        if not mount_path:
            raise ValueError("litefs_mount_path must be provided in OPTIONS")

        # Validate mount_path exists (fail-fast) (DJANGO-027)
        mount_path_obj = Path(mount_path)
        if not mount_path_obj.exists():
            raise LiteFSNotRunningError(
                f"LiteFS mount path does not exist: {mount_path}. "
                "LiteFS may not be running or mounted."
            )

        # Update database path to be in mount_path
        original_name = settings_dict.get("NAME", "db.sqlite3")
        settings_dict = settings_dict.copy()
        settings_dict["NAME"] = str(mount_path_obj / original_name)

        # Initialize parent SQLite3 backend
        super().__init__(
            settings_dict, alias=alias, allow_thread_sharing=allow_thread_sharing
        )

        # Create PrimaryDetector use case (Clean Architecture: delegate to use case)
        # Mount path validation already done above (fail-fast)
        self._primary_detector = PrimaryDetector(mount_path)
        self._mount_path = mount_path

    def get_new_connection(self, conn_params):
        """Create new database connection with IMMEDIATE transaction mode.

        Raises:
            LiteFSNotRunningError: If mount_path doesn't exist (DJANGO-025)
        """
        # Validate mount_path exists before attempting connection (DJANGO-025)
        # This provides clear error handling and prevents inconsistent error types
        mount_path_obj = Path(self._mount_path)
        if not mount_path_obj.exists():
            raise LiteFSNotRunningError(
                f"LiteFS mount path does not exist: {self._mount_path}. "
                "Cannot create database connection. LiteFS may not be running or mounted."
            )

        # Set transaction mode to IMMEDIATE for better lock handling
        conn_params.setdefault("isolation_level", None)
        connection = super().get_new_connection(conn_params)

        # Set IMMEDIATE transaction mode
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL")  # LiteFS requires WAL
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("COMMIT")

        return connection

    def create_cursor(self, name=None):
        """Create cursor with primary detection."""
        return LiteFSCursor(self.connection, self._primary_detector)

    def _start_transaction_under_autocommit(self):
        """Start transaction with IMMEDIATE mode for better lock handling.

        Overrides Django's default BEGIN (DEFERRED) to use BEGIN IMMEDIATE,
        which acquires a write lock immediately and prevents lock contention
        under concurrent load. This is required for LiteFS's single-writer model.
        """
        self.cursor().execute("BEGIN IMMEDIATE")
