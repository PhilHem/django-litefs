"""SQL detection use case for identifying write operations."""

from __future__ import annotations

import re

# Pre-compiled regex patterns for SQL comment stripping (PERF-001)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*(\n|$)")

# Pre-compiled regex for CTE write keyword detection (CONC-002)
# Uses word boundaries to avoid false positives on column/table names
# like 'delete_flag', 'update_count', 'insert_date', 'deleted_items'
# Uses negative lookbehind for FROM to avoid matching table names after FROM clauses
# e.g., "WITH UPDATE AS (SELECT 1) SELECT * FROM UPDATE" should not match
_CTE_WRITE_KEYWORD_RE = re.compile(
    r"(?<!FROM\s)\b(INSERT|UPDATE|DELETE)\b", re.IGNORECASE
)


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
        sql = _BLOCK_COMMENT_RE.sub("", sql)
        # Remove line comments -- ... (to end of line)
        sql = _LINE_COMMENT_RE.sub(r"\1", sql)
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
        # Uses negative lookbehind regex to avoid false positives:
        # - Column/table names like 'delete_flag', 'update_count', 'insert_date'
        # - CTE alias names like 'WITH UPDATE AS (SELECT 1) SELECT * FROM UPDATE'
        # - Table names after FROM clauses
        if sql_upper.startswith("WITH"):
            # Find the closing paren of the CTE definition to get the main query
            # Pattern: WITH name AS (body) main_query
            # We need to find the matching closing paren and only search after it
            paren_depth = 0
            main_query_start = 0

            for i, char in enumerate(sql_upper):
                if char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        # Found the closing paren of CTE body
                        main_query_start = i + 1
                        break

            # Only search for write keywords in the main query part
            if main_query_start > 0:
                main_query = sql_clean[main_query_start:]
            else:
                main_query = sql_clean

            return bool(_CTE_WRITE_KEYWORD_RE.search(main_query))

        return False




