"""Unit tests for SQL detection use case."""

from __future__ import annotations

import pytest

from litefs.usecases.sql_detector import SQLDetector


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestSQLDetector:
    """Test SQL detection logic."""

    def test_strip_sql_comments_removes_block_comments(self):
        """Test that block comments are removed."""
        detector = SQLDetector()
        sql = "SELECT /* comment */ * FROM table"
        result = detector.strip_sql_comments(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "comment" not in result

    def test_strip_sql_comments_removes_line_comments(self):
        """Test that line comments are removed."""
        detector = SQLDetector()
        sql = "SELECT * FROM table -- this is a comment\nWHERE id = 1"
        result = detector.strip_sql_comments(sql)
        assert "--" not in result or result.find("--") > result.find("\n")

    def test_is_write_operation_direct_keywords(self):
        """Test detection of direct write keywords."""
        detector = SQLDetector()
        assert detector.is_write_operation("INSERT INTO test VALUES (1)") is True
        assert detector.is_write_operation("UPDATE test SET x = 1") is True
        assert detector.is_write_operation("DELETE FROM test") is True
        assert detector.is_write_operation("CREATE TABLE test (id INT)") is True
        assert detector.is_write_operation("DROP TABLE test") is True
        assert detector.is_write_operation("SELECT * FROM test") is False

    def test_is_write_operation_cte_patterns(self):
        """Test CTE write pattern detection."""
        detector = SQLDetector()
        assert detector.is_write_operation("WITH cte AS (SELECT 1) INSERT INTO test VALUES (1)") is True
        assert detector.is_write_operation("WITH cte AS (SELECT 1) UPDATE test SET x = 1") is True
        assert detector.is_write_operation("WITH cte AS (SELECT 1) DELETE FROM test") is True
        assert detector.is_write_operation("WITH cte AS (SELECT 1) SELECT * FROM cte") is False

    def test_is_write_operation_pragma_assignments(self):
        """Test PRAGMA write detection."""
        detector = SQLDetector()
        assert detector.is_write_operation("PRAGMA user_version = 1") is True
        assert detector.is_write_operation("PRAGMA schema_version = 2") is True
        assert detector.is_write_operation("PRAGMA journal_mode") is False

    def test_is_write_operation_with_comments(self):
        """Test write detection with SQL comments."""
        detector = SQLDetector()
        assert detector.is_write_operation("/* comment */ INSERT INTO test VALUES (1)") is True
        assert detector.is_write_operation("-- comment\nINSERT INTO test VALUES (1)") is True
        assert detector.is_write_operation("/* comment */ SELECT * FROM test") is False

    def test_is_write_operation_cte_with_update_alias(self):
        """Test CTE with UPDATE as alias name (false positive regression test)."""
        detector = SQLDetector()
        # CTE with UPDATE as alias should not be detected as write
        assert detector.is_write_operation("WITH UPDATE AS (SELECT 1) SELECT * FROM UPDATE") is False
        # CTE with INSERT as alias should not be detected as write
        assert detector.is_write_operation("WITH INSERT AS (SELECT 1) SELECT * FROM INSERT") is False
        # CTE with DELETE as alias should not be detected as write
        assert detector.is_write_operation("WITH DELETE AS (SELECT 1) SELECT * FROM DELETE") is False
        # But actual write operation in CTE should still be detected
        assert detector.is_write_operation("WITH UPDATE AS (SELECT 1) UPDATE test SET x = 1") is True

