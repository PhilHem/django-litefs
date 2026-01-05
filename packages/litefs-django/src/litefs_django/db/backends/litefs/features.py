"""Database features for LiteFS backend."""

from django.db.backends.sqlite3.features import (
    DatabaseFeatures as SQLite3DatabaseFeatures,
)


class DatabaseFeatures(SQLite3DatabaseFeatures):
    """Database features for LiteFS backend.

    Inherits all SQLite3 features. LiteFS requires WAL mode, which is
    automatically configured in the backend.
    """

    # LiteFS requires WAL mode (configured in get_new_connection)
    # All other features are the same as SQLite3








