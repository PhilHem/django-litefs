"""Property-based tests for SQL parsing methods.

Verifies:
- RAFT-005: strip_sql_comments() idempotence and correctness
- RAFT-006: is_write_operation() word boundaries and case handling
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from litefs.usecases.sql_detector import SQLDetector


# Strategy for generating SQL-like strings (without actual comments initially)
sql_identifier = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
    min_size=1,
    max_size=20,
)

# Strategy for SQL keywords that might appear in column/table names
sql_like_names = st.sampled_from([
    "delete_flag",
    "update_count",
    "insert_date",
    "deleted_items",
    "updated_at",
    "inserted_by",
    "create_time",
    "drop_zone",
    "alter_ego",
])

# Strategy for write keywords
write_keywords = st.sampled_from([
    "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE",
    "VACUUM", "REINDEX", "ANALYZE", "ATTACH", "DETACH",
    "SAVEPOINT", "RELEASE", "ROLLBACK",
])


# Create a module-level detector for property tests
# (Hypothesis @given doesn't work with pytest fixtures)
_test_detector = SQLDetector()


@pytest.mark.tra("Adapter")
class TestStripSqlCommentsProperties:
    """RAFT-005: Property-based tests for strip_sql_comments()."""

    @pytest.mark.tier(3)
    @given(sql=st.text(max_size=200))
    @settings(max_examples=100)
    def test_strip_comments_idempotent(self, sql: str):
        """Stripping comments twice should equal stripping once."""
        once = _test_detector.strip_sql_comments(sql)
        twice = _test_detector.strip_sql_comments(once)
        assert once == twice, f"Not idempotent: strip('{sql}') = '{once}', strip again = '{twice}'"

    @pytest.mark.tier(3)
    @given(
        prefix=st.text(alphabet="SELECT FROM WHERE ", max_size=20),
        comment=st.text(max_size=50),
        suffix=st.text(alphabet="SELECT FROM WHERE ", max_size=20),
    )
    @settings(max_examples=100)
    def test_strip_comments_removes_block_comments(
        self, prefix: str, comment: str, suffix: str
    ):
        """Block comments /* ... */ should be removed."""
        # Avoid nested comment markers in the comment content
        assume("/*" not in comment and "*/" not in comment)

        sql = f"{prefix}/*{comment}*/{suffix}"
        result = _test_detector.strip_sql_comments(sql)

        assert "/*" not in result, f"Block comment start still present in: {result}"
        assert "*/" not in result, f"Block comment end still present in: {result}"

    @pytest.mark.tier(3)
    @given(
        prefix=st.text(alphabet="SELECT FROM WHERE ", max_size=20),
        comment=st.text(alphabet="comment text here", max_size=30),
    )
    @settings(max_examples=100)
    def test_strip_comments_removes_line_comments(self, prefix: str, comment: str):
        """Line comments -- ... should be removed."""
        # Avoid newlines in comment (they terminate line comments)
        assume("\n" not in comment)

        sql = f"{prefix}--{comment}\n"
        result = _test_detector.strip_sql_comments(sql)

        # The -- and comment should be gone, but newline preserved
        assert "--" not in result, f"Line comment marker still present in: {result}"

    @pytest.mark.tier(3)
    @given(sql=st.text(alphabet=" \t\n", max_size=20))
    @settings(max_examples=50)
    def test_strip_comments_preserves_whitespace_only(self, sql: str):
        """Whitespace-only input should be preserved."""
        result = _test_detector.strip_sql_comments(sql)
        # Whitespace should be preserved (no comments to strip)
        assert result == sql


@pytest.mark.tra("Adapter")
class TestIsWriteOperationProperties:
    """RAFT-006: Property-based tests for is_write_operation()."""

    @pytest.mark.tier(3)
    @given(keyword=write_keywords)
    @settings(max_examples=50)
    def test_write_keywords_case_insensitive(self, keyword: str):
        """Write keywords should be detected regardless of case."""
        # Test various case combinations
        sql_upper = f"{keyword.upper()} INTO test VALUES (1)"
        sql_lower = f"{keyword.lower()} into test values (1)"
        sql_mixed = f"{keyword.capitalize()} Into Test Values (1)"

        # All should be detected as writes (if they start the statement)
        if keyword.upper() in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
                               "ALTER", "REPLACE", "VACUUM", "REINDEX", "ANALYZE",
                               "ATTACH", "DETACH", "SAVEPOINT", "RELEASE", "ROLLBACK"):
            assert _test_detector.is_write_operation(sql_upper) is True, f"Failed for: {sql_upper}"
            assert _test_detector.is_write_operation(sql_lower) is True, f"Failed for: {sql_lower}"
            assert _test_detector.is_write_operation(sql_mixed) is True, f"Failed for: {sql_mixed}"

    @pytest.mark.tier(3)
    @given(sql=st.text(alphabet=" \t\n", max_size=20))
    @settings(max_examples=50)
    def test_empty_or_whitespace_not_write(self, sql: str):
        """Empty or whitespace-only SQL should not be a write."""
        assert _test_detector.is_write_operation(sql) is False
        assert _test_detector.is_write_operation("") is False

    @pytest.mark.tier(3)
    @given(column_name=sql_like_names)
    @settings(max_examples=50)
    def test_cte_word_boundary_no_false_positives(self, column_name: str):
        """Column names containing write keywords should not trigger false positives."""
        # SELECT with columns that have write-keyword substrings
        sql = f"SELECT {column_name} FROM my_table WHERE id = 1"
        assert _test_detector.is_write_operation(sql) is False, (
            f"False positive: '{column_name}' in SELECT was detected as write"
        )

    @pytest.mark.tier(3)
    @given(
        cte_name=sql_identifier,
        keyword=st.sampled_from(["INSERT", "UPDATE", "DELETE"]),
    )
    @settings(max_examples=50)
    def test_cte_write_detection(self, cte_name: str, keyword: str):
        """CTEs with actual write operations should be detected."""
        sql = f"WITH {cte_name} AS (SELECT 1) {keyword} INTO test VALUES (1)"
        assert _test_detector.is_write_operation(sql) is True, f"CTE write not detected: {sql}"

    @pytest.mark.tier(3)
    @given(cte_name=sql_identifier)
    @settings(max_examples=50)
    def test_cte_select_not_write(self, cte_name: str):
        """CTEs with only SELECT should not be detected as writes."""
        sql = f"WITH {cte_name} AS (SELECT 1) SELECT * FROM {cte_name}"
        assert _test_detector.is_write_operation(sql) is False, f"CTE SELECT falsely detected as write: {sql}"

    @pytest.mark.tier(3)
    @given(
        comment=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", max_size=30),
        keyword=st.sampled_from(["INSERT", "UPDATE", "DELETE"]),
    )
    @settings(max_examples=50)
    def test_write_after_block_comment(self, comment: str, keyword: str):
        """Write keywords after block comments should be detected."""
        assume("/*" not in comment and "*/" not in comment)

        sql = f"/*{comment}*/ {keyword} INTO test VALUES (1)"
        assert _test_detector.is_write_operation(sql) is True, f"Write after comment not detected: {sql}"

    @pytest.mark.tier(3)
    @given(
        comment=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", max_size=30),
        keyword=st.sampled_from(["INSERT", "UPDATE", "DELETE"]),
    )
    @settings(max_examples=50)
    def test_write_after_line_comment(self, comment: str, keyword: str):
        """Write keywords after line comments should be detected."""
        assume("\n" not in comment)

        sql = f"--{comment}\n{keyword} INTO test VALUES (1)"
        assert _test_detector.is_write_operation(sql) is True, f"Write after line comment not detected: {sql}"


@pytest.mark.tra("Adapter")
class TestPragmaWriteDetection:
    """Additional tests for PRAGMA write detection."""

    @pytest.mark.tier(3)
    @given(pragma_name=sql_identifier, value=st.integers(min_value=0, max_value=1000))
    @settings(max_examples=50)
    def test_pragma_with_assignment_is_write(self, pragma_name: str, value: int):
        """PRAGMA statements with = assignment should be writes."""
        sql = f"PRAGMA {pragma_name} = {value}"
        assert _test_detector.is_write_operation(sql) is True, f"PRAGMA assignment not detected: {sql}"

    @pytest.mark.tier(3)
    @given(pragma_name=sql_identifier)
    @settings(max_examples=50)
    def test_pragma_without_assignment_not_write(self, pragma_name: str):
        """PRAGMA statements without = assignment should not be writes."""
        assume("=" not in pragma_name)

        sql = f"PRAGMA {pragma_name}"
        assert _test_detector.is_write_operation(sql) is False, f"PRAGMA read falsely detected as write: {sql}"
