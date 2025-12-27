"""LiteFS database backend base implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings as django_settings
from django.db.backends.sqlite3.base import (
    DatabaseWrapper as SQLite3DatabaseWrapper,
    SQLiteCursorWrapper as SQLite3Cursor,
)

from litefs.adapters.ports import PrimaryDetectorPort, SplitBrainDetectorPort
from litefs.usecases.mount_validator import MountValidator
from litefs.usecases.primary_detector import PrimaryDetector
from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs.usecases.sql_detector import SQLDetector
from litefs_django.exceptions import NotPrimaryError, SplitBrainError
from litefs_django.settings import is_dev_mode

if TYPE_CHECKING:
    from sqlite3 import Connection


class LiteFSCursor(SQLite3Cursor):
    """Cursor with primary detection and split-brain detection for write operations."""

    def __init__(
        self,
        connection: "Connection",
        primary_detector: PrimaryDetectorPort,
        split_brain_detector: SplitBrainDetector | None = None,
        dev_mode: bool = False,
    ) -> None:
        """Initialize LiteFS cursor.

        Args:
            connection: Database connection
            primary_detector: PrimaryDetector use case instance (or any
                implementation of PrimaryDetectorPort protocol)
            split_brain_detector: Optional SplitBrainDetector use case instance
                for detecting split-brain conditions. If provided, split-brain
                check is performed BEFORE primary status check on write operations.
            dev_mode: If True, skip all LiteFS-specific checks (primary, split-brain).
        """
        super().__init__(connection)
        self._primary_detector = primary_detector
        self._split_brain_detector = split_brain_detector
        self._sql_detector = SQLDetector()
        self._dev_mode = dev_mode

    def _check_split_brain_before_write(self, sql: str) -> None:
        """Check for split-brain condition before write operations.

        Args:
            sql: SQL statement to check

        Raises:
            SplitBrainError: If split-brain is detected on a write operation
        """
        # Skip checks in dev mode
        if self._dev_mode:
            return

        if not self._split_brain_detector:
            # No detector provided, skip check
            return

        if self._sql_detector.is_write_operation(sql):
            try:
                split_brain_status = self._split_brain_detector.detect_split_brain()
                if split_brain_status.is_split_brain:
                    leader_count = len(split_brain_status.leader_nodes)
                    raise SplitBrainError(
                        f"Write operation attempted during split-brain condition. "
                        f"Detected {leader_count} leaders: {split_brain_status.leader_nodes}. "
                        f"Writes are not allowed during split-brain to prevent data inconsistency."
                    )
            except SplitBrainError:
                raise
            except Exception:
                # Re-raise other exceptions (e.g., network errors from detector)
                raise

    def _check_primary_before_write(self, sql: str) -> None:
        """Check if this node is primary before write operations.

        This check is performed AFTER split-brain check.

        Args:
            sql: SQL statement to check

        Raises:
            NotPrimaryError: If this node is not primary (replica)
        """
        # Skip checks in dev mode
        if self._dev_mode:
            return

        if self._sql_detector.is_write_operation(sql):
            try:
                if not self._primary_detector.is_primary():
                    raise NotPrimaryError(
                        "This node is not primary (replica). "
                        "Write operation attempted on replica node. "
                        "Only the primary node can perform writes."
                    )
            except NotPrimaryError:
                raise
            except Exception:
                # Re-raise other exceptions (e.g., LiteFSNotRunningError)
                raise

    def execute(self, sql, params=None):
        """Execute SQL statement with split-brain and primary checks for write operations.

        Split-brain check is performed BEFORE primary status check.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Query result

        Raises:
            SplitBrainError: If split-brain detected on write
            NotPrimaryError: If write attempted on replica
        """
        self._check_split_brain_before_write(sql)
        self._check_primary_before_write(sql)
        return super().execute(sql, params)

    def executemany(self, sql, param_list):
        """Execute SQL statement multiple times with split-brain and primary checks.

        Split-brain check is performed BEFORE primary status check.

        Args:
            sql: SQL statement
            param_list: List of parameter tuples

        Returns:
            Query result

        Raises:
            SplitBrainError: If split-brain detected on write
            NotPrimaryError: If write attempted on replica
        """
        self._check_split_brain_before_write(sql)
        self._check_primary_before_write(sql)
        return super().executemany(sql, param_list)

    def executescript(self, sql_script):
        """Execute SQL script with split-brain and primary checks (DJANGO-028).

        Scripts can contain multiple statements including writes, so we
        require split-brain and primary status before execution.

        Split-brain check is performed BEFORE primary status check.

        Args:
            sql_script: SQL script containing multiple statements

        Returns:
            Cursor

        Raises:
            SplitBrainError: If split-brain detected
            NotPrimaryError: If attempted on replica
        """
        # Skip checks in dev mode
        if self._dev_mode:
            return super().executescript(sql_script)

        # Check split-brain first (scripts can be writes)
        if self._split_brain_detector:
            try:
                split_brain_status = self._split_brain_detector.detect_split_brain()
                if split_brain_status.is_split_brain:
                    leader_count = len(split_brain_status.leader_nodes)
                    raise SplitBrainError(
                        f"Script execution attempted during split-brain condition. "
                        f"Detected {leader_count} leaders: {split_brain_status.leader_nodes}. "
                        f"Scripts may contain writes and are not allowed during split-brain."
                    )
            except SplitBrainError:
                raise
            except Exception:
                raise

        # Then check primary status
        if not self._primary_detector.is_primary():
            raise NotPrimaryError(
                "This node is not primary (replica). "
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
        split_brain_detector: SplitBrainDetector | None = None,
    ) -> None:
        """Initialize LiteFS database backend.

        Args:
            settings_dict: Django database settings dict
            alias: Database alias
            primary_detector: Optional PrimaryDetector instance for dependency
                injection. If not provided, a new PrimaryDetector is created.
                Use this for testing with FakePrimaryDetector.
            split_brain_detector: Optional SplitBrainDetector instance for dependency
                injection. If not provided, a new SplitBrainDetector is created.
                Use this for testing with FakeSplitBrainDetector.
        """
        # Check if dev mode is enabled
        litefs_config = getattr(django_settings, "LITEFS", None)
        self._dev_mode = is_dev_mode(litefs_config)

        # Extract OPTIONS for configuration validation
        options = settings_dict.get("OPTIONS", {})

        # Validate transaction_mode early (before mount path validation)
        transaction_mode = options.get("transaction_mode", "IMMEDIATE")
        valid_modes = {"DEFERRED", "IMMEDIATE", "EXCLUSIVE"}
        if transaction_mode not in valid_modes:
            raise ValueError(
                f"Invalid transaction_mode '{transaction_mode}'. "
                f"Must be one of: {', '.join(sorted(valid_modes))}"
            )

        # Extract LiteFS mount path from OPTIONS
        mount_path = options.get("litefs_mount_path")

        # Initialize detectors (used in both dev and production mode)
        if primary_detector is not None:
            primary_detector_instance: PrimaryDetectorPort = primary_detector
        else:
            # Create a detector - in dev mode it won't be used, but needed for type consistency
            primary_detector_instance = PrimaryDetector(mount_path or "/tmp")

        if split_brain_detector is not None:
            split_brain_detector_instance: SplitBrainDetector | None = (
                split_brain_detector
            )
        else:
            split_brain_detector_instance = None

        if self._dev_mode:
            # In dev mode, skip mount path validation and use standard SQLite behavior
            # Use the original NAME path directly (don't modify it)
            original_name = settings_dict.get("NAME", "db.sqlite3")
            settings_dict = settings_dict.copy()
            # Keep original path (don't prepend mount_path)
            settings_dict["NAME"] = original_name

            # Initialize parent SQLite3 backend (Django 5.x)
            super().__init__(settings_dict, alias=alias)

            # Store detectors (won't be used in dev mode, but needed for type consistency)
            self._primary_detector = primary_detector_instance
            self._split_brain_detector = split_brain_detector_instance
            self._mount_path = mount_path or "/tmp"

            # Store validated transaction mode
            self._transaction_mode = transaction_mode
            return

        # Production mode: validate mount path and use LiteFS behavior
        if not mount_path:
            raise ValueError("litefs_mount_path is required in OPTIONS")

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

        # Store detectors
        self._primary_detector = primary_detector_instance
        self._split_brain_detector = split_brain_detector_instance
        self._mount_path = mount_path

        # Store validated transaction mode
        self._transaction_mode = transaction_mode

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
        # Skip mount path validation in dev mode
        if not self._dev_mode:
            # Validate mount_path exists before attempting connection (DJANGO-025)
            # This provides clear error handling and prevents inconsistent error types
            mount_path_obj = Path(self._mount_path)
            validator = MountValidator()
            validator.validate(mount_path_obj)

        # Set transaction mode to configured value (default: IMMEDIATE)
        conn_params.setdefault("isolation_level", None)
        connection = super().get_new_connection(conn_params)

        # In production mode, set WAL mode and transaction mode (LiteFS requires WAL)
        # In dev mode, skip these settings (standard SQLite behavior)
        if not self._dev_mode:
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")  # LiteFS requires WAL
                cursor.execute(f"BEGIN {self._transaction_mode}")
                cursor.execute("COMMIT")
            finally:
                cursor.close()

        return connection

    def create_cursor(self, name=None):
        """Create cursor with primary detection and split-brain detection."""
        return LiteFSCursor(
            self.connection,
            primary_detector=self._primary_detector,
            split_brain_detector=self._split_brain_detector,
            dev_mode=self._dev_mode,
        )

    def _start_transaction_under_autocommit(self):
        """Start transaction with configured mode for better lock handling.

        Overrides Django's default BEGIN (DEFERRED) to use configured transaction mode
        (default: IMMEDIATE), which acquires a write lock immediately and prevents lock
        contention under concurrent load. This is required for LiteFS's single-writer model.
        """
        self.cursor().execute(f"BEGIN {self._transaction_mode}")
