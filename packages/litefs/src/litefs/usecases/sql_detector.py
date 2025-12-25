"""SQL detection use case for identifying write operations."""

from __future__ import annotations

import re

# Pre-compiled regex patterns for SQL comment stripping (PERF-001)
_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)
_LINE_COMMENT_RE = re.compile(r'--[^\n]*(\n|$)')

# Pre-compiled regex for CTE write keyword detection (CONC-002)
# Uses word boundaries to avoid false positives on column/table names
# like 'delete_flag', 'update_count', 'insert_date', 'deleted_items'
_CTE_WRITE_KEYWORD_RE = re.compile(r'\b(INSERT|UPDATE|DELETE)\b', re.IGNORECASE)


class SQLDetector:
    """Detects SQL write operations.

    Handles:
    - Direct write keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, REPLACE)
    - Database maintenance operations (VACUUM, REINDEX, ANALYZE)
    - ATTACH/DETACH DATABASE statements
    - SAVEPOINT/RELEASE/ROLLBACK statements
    - State-modifying PRAGMA statements
    - CTE patterns: WITH ... INSERT/UPDATE/DELETE
    - SQL with leading comments
    """

    def strip_sql_comments(self, sql: str) -> str:
        """Remove SQL comments for write detection.

        Removes both block comments (/* ... */) and line comments (-- ...).
        Uses pre-compiled regex patterns at module level (PERF-001).

        Args:
            sql: SQL statement string

        Returns:
            SQL string with comments removed
        """
        # Remove block comments /* ... */ (non-greedy, handles nested)
        sql = _BLOCK_COMMENT_RE.sub('', sql)
        # Remove line comments -- ... (to end of line)
        sql = _LINE_COMMENT_RE.sub(r'\1', sql)
        return sql

    def is_write_operation(self, sql: str) -> bool:
        """Check if SQL statement is a write operation.

        Args:
            sql: SQL statement string

        Returns:
            True if statement is a write operation
        """
        if not sql:
            return False

        # Strip comments before detection
        sql_clean = self.strip_sql_comments(sql)
        sql_upper = sql_clean.strip().upper()

        if not sql_upper:
            return False

        # Direct write keywords (existing + maintenance ops)
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
            # ATTACH/DETACH DATABASE
            "ATTACH",
            "DETACH",
            # SAVEPOINT operations
            "SAVEPOINT",
            "RELEASE",
            "ROLLBACK",
        )

        if any(sql_upper.startswith(keyword) for keyword in write_keywords):
            return True

        # PRAGMA write detection (only when assignment operator present)
        # e.g., PRAGMA user_version = 1, PRAGMA schema_version = 1
        if sql_upper.startswith("PRAGMA") and "=" in sql_clean:
            return True

        # CTE pattern detection: WITH ... INSERT/UPDATE/DELETE
        # Uses word boundary regex to avoid false positives on column/table names
        # like 'delete_flag', 'update_count', 'insert_date', 'deleted_items'
        if sql_upper.startswith("WITH"):
            return bool(_CTE_WRITE_KEYWORD_RE.search(sql_clean))

        return False

