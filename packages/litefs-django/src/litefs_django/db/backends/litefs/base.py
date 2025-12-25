"""LiteFS database backend base implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.db.backends.sqlite3.base import (
    DatabaseWrapper as SQLite3DatabaseWrapper,
    SQLiteCursorWrapper as SQLite3Cursor,
)

from litefs.adapters.ports import PrimaryDetectorPort
from litefs.usecases.mount_validator import MountValidator
from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.sql_detector import SQLDetector
from litefs_django.exceptions import NotPrimaryError

if TYPE_CHECKING:
    from sqlite3 import Connection


class LiteFSCursor(SQLite3Cursor):
    """Cursor with primary detection for write operations."""

    def __init__(
        self, connection: "Connection", primary_detector: PrimaryDetectorPort
    ) -> None:
        """Initialize LiteFS cursor.

        Args:
            connection: Database connection
            primary_detector: PrimaryDetector use case instance (or any
                implementation of PrimaryDetectorPort protocol)
        """
        super().__init__(connection)
        self._primary_detector = primary_detector
        self._sql_detector = SQLDetector()

    def _check_primary_before_write(self, sql):
        """Check if this node is primary before write operations.

        Args:
            sql: SQL statement to check

        Raises:
            NotPrimaryError: If this node is not primary (replica)
        """
        if self._sql_detector.is_write_operation(sql):
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

    def __init__(
        self,
        settings_dict: dict,
        alias: str = "default",
        *,
        primary_detector: PrimaryDetectorPort | None = None,
    ) -> None:
        """Initialize LiteFS database backend.

        Args:
            settings_dict: Django database settings dict
            alias: Database alias
            primary_detector: Optional PrimaryDetector instance for dependency
                injection. If not provided, a new PrimaryDetector is created.
                Use this for testing with FakePrimaryDetector.
        """
        # Extract LiteFS mount path from OPTIONS
        options = settings_dict.get("OPTIONS", {})
        mount_path = options.get("litefs_mount_path")

        if not mount_path:
            raise ValueError("litefs_mount_path must be provided in OPTIONS")

        # Validate mount_path using MountValidator (fail-fast) (DJANGO-027)
        mount_path_obj = Path(mount_path)
        validator = MountValidator()
        validator.validate(mount_path_obj)

        # Update database path to be in mount_path
        original_name = settings_dict.get("NAME", "db.sqlite3")
        settings_dict = settings_dict.copy()
        settings_dict["NAME"] = str(mount_path_obj / original_name)

        # Initialize parent SQLite3 backend (Django 5.x)
        super().__init__(settings_dict, alias=alias)

        # Use injected detector or create PrimaryDetector use case
        # (Clean Architecture: delegate to use case, allow DI for testing)
        if primary_detector is not None:
            self._primary_detector: PrimaryDetectorPort = primary_detector
        else:
            self._primary_detector = PrimaryDetector(mount_path)
        self._mount_path = mount_path

        # Extract transaction mode from OPTIONS (default: IMMEDIATE)
        self._transaction_mode = options.get("transaction_mode", "IMMEDIATE")

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
        """Create new database connection with configured transaction mode.

        Raises:
            LiteFSNotRunningError: If mount_path doesn't exist (DJANGO-025)
        """
        # Validate mount_path exists before attempting connection (DJANGO-025)
        # This provides clear error handling and prevents inconsistent error types
        mount_path_obj = Path(self._mount_path)
        validator = MountValidator()
        validator.validate(mount_path_obj)

        # Set transaction mode to configured value (default: IMMEDIATE)
        conn_params.setdefault("isolation_level", None)
        connection = super().get_new_connection(conn_params)

        # Set configured transaction mode
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")  # LiteFS requires WAL
            cursor.execute(f"BEGIN {self._transaction_mode}")
            cursor.execute("COMMIT")
        finally:
            cursor.close()

        return connection

    def create_cursor(self, name=None):
        """Create cursor with primary detection."""
        return LiteFSCursor(self.connection, self._primary_detector)

    def _start_transaction_under_autocommit(self):
        """Start transaction with configured mode for better lock handling.

        Overrides Django's default BEGIN (DEFERRED) to use configured transaction mode
        (default: IMMEDIATE), which acquires a write lock immediately and prevents lock
        contention under concurrent load. This is required for LiteFS's single-writer model.
        """
        self.cursor().execute(f"BEGIN {self._transaction_mode}")





