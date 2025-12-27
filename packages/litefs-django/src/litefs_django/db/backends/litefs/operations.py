"""Database operations for LiteFS backend."""

from django.db.backends.sqlite3.operations import (
    DatabaseOperations as SQLite3DatabaseOperations,
)


class DatabaseOperations(SQLite3DatabaseOperations):
    """Database operations for LiteFS backend.

    Inherits all SQLite3 operations. No overrides needed for basic functionality.
    LiteFS-specific behavior (primary detection, transaction mode) is handled
    in the DatabaseWrapper and Cursor classes.
    """

    # All operations are the same as SQLite3
    # Primary detection and transaction mode are handled in base.py





