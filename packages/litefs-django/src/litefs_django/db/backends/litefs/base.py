"""LiteFS database backend base implementation."""

from pathlib import Path

from django.db.backends.sqlite3.base import (
    DatabaseWrapper as SQLite3DatabaseWrapper,
    SQLiteCursorWrapper as SQLite3Cursor,
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

    def _strip_sql_comments(self, sql):
        """Remove SQL comments for write detection (DJANGO-031).

        Removes both block comments (/* ... */) and line comments (-- ...).
        """
        import re
        # Remove block comments /* ... */ (non-greedy, handles nested)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # Remove line comments -- ... (to end of line)
        sql = re.sub(r'--[^\n]*(\n|$)', r'\1', sql)
        return sql

    def _is_write_operation(self, sql):
        """Check if SQL statement is a write operation.

        Handles:
        - Direct write keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, REPLACE)
        - Database maintenance operations (VACUUM, REINDEX, ANALYZE) (DJANGO-030)
        - CTE patterns: WITH ... INSERT/UPDATE/DELETE (DJANGO-029)
        - SQL with leading comments (DJANGO-031)

        Args:
            sql: SQL statement string

        Returns:
            True if statement is a write operation
        """
        if not sql:
            return False

        # Strip comments before detection (DJANGO-031)
        sql_clean = self._strip_sql_comments(sql)
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

        # CTE pattern detection (DJANGO-029): WITH ... INSERT/UPDATE/DELETE
        if sql_upper.startswith("WITH"):
            cte_write_keywords = ("INSERT", "UPDATE", "DELETE")
            return any(keyword in sql_upper for keyword in cte_write_keywords)

        return False

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

    def executescript(self, sql_script):
        """Execute SQL script with primary check (DJANGO-028).

        Scripts can contain multiple statements including writes, so we
        require primary status before execution.

        Args:
            sql_script: SQL script containing multiple statements

        Returns:
            Cursor

        Raises:
            NotPrimaryError: If attempted on replica
        """
        if not self._primary_detector.is_primary():
            raise NotPrimaryError(
                "Script execution attempted on replica node. "
                "Only the primary node can execute scripts that may contain writes."
            )
        return super().executescript(sql_script)


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

    def __init__(self, settings_dict, alias="default"):
        """Initialize LiteFS database backend.

        Args:
            settings_dict: Django database settings dict
            alias: Database alias
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

        # Initialize parent SQLite3 backend (Django 5.x)
        super().__init__(settings_dict, alias=alias)

        # Create PrimaryDetector use case (Clean Architecture: delegate to use case)
        # Mount path validation already done above (fail-fast)
        self._primary_detector = PrimaryDetector(mount_path)
        self._mount_path = mount_path

    def get_connection_params(self):
        """Get connection params without litefs_mount_path.

        Override to remove litefs_mount_path from OPTIONS before
        passing to sqlite3.connect().
        """
        params = super().get_connection_params()
        # Remove litefs_mount_path - it's for our use, not sqlite3
        params.pop("litefs_mount_path", None)
        return params

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
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")  # LiteFS requires WAL
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("COMMIT")
        finally:
            cursor.close()

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
