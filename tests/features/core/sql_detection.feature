# @bdd-decomposed: 2025-12-26 status=implemented
Feature: SQL Write Operation Detection
  SQL statements are classified as read or write operations.
  This enables blocking writes on replicas and during split-brain conditions.

  The SQLDetector identifies SQL statements that modify database state. Detection
  must be accurate to avoid false positives (blocking reads) and false negatives
  (allowing writes on replicas). The detector handles:
  - Direct write keywords (INSERT, UPDATE, DELETE, etc.)
  - Database maintenance operations (VACUUM, REINDEX, ANALYZE)
  - Transaction control statements (SAVEPOINT, RELEASE, ROLLBACK)
  - State-modifying PRAGMA statements (only with assignment operator)
  - Common Table Expressions (CTE) with write operations
  - SQL statements with leading comments

  # ---------------------------------------------------------------------------
  # Direct Write Keywords
  # ---------------------------------------------------------------------------

  Scenario: INSERT is detected as write operation
    When I check if "INSERT INTO users (name) VALUES ('test')" is a write
    Then is_write_operation should return true

  Scenario: UPDATE is detected as write operation
    When I check if "UPDATE users SET name = 'test'" is a write
    Then is_write_operation should return true

  Scenario: DELETE is detected as write operation
    When I check if "DELETE FROM users WHERE id = 1" is a write
    Then is_write_operation should return true

  Scenario: REPLACE is detected as write operation
    When I check if "REPLACE INTO users (id, name) VALUES (1, 'test')" is a write
    Then is_write_operation should return true

  Scenario: CREATE is detected as write operation
    When I check if "CREATE TABLE test (id INTEGER)" is a write
    Then is_write_operation should return true

  Scenario: DROP is detected as write operation
    When I check if "DROP TABLE test" is a write
    Then is_write_operation should return true

  Scenario: ALTER is detected as write operation
    When I check if "ALTER TABLE test ADD COLUMN name TEXT" is a write
    Then is_write_operation should return true

  # ---------------------------------------------------------------------------
  # Database Maintenance Operations
  # ---------------------------------------------------------------------------

  Scenario: VACUUM is detected as write operation
    When I check if "VACUUM" is a write
    Then is_write_operation should return true

  Scenario: REINDEX is detected as write operation
    When I check if "REINDEX test_index" is a write
    Then is_write_operation should return true

  Scenario: ANALYZE is detected as write operation
    When I check if "ANALYZE users" is a write
    Then is_write_operation should return true

  # ---------------------------------------------------------------------------
  # Database Lifecycle Operations
  # ---------------------------------------------------------------------------

  Scenario: ATTACH is detected as write operation
    When I check if "ATTACH DATABASE 'test.db' AS test" is a write
    Then is_write_operation should return true

  Scenario: DETACH is detected as write operation
    When I check if "DETACH DATABASE test" is a write
    Then is_write_operation should return true

  # ---------------------------------------------------------------------------
  # Transaction Control Statements
  # ---------------------------------------------------------------------------

  Scenario: SAVEPOINT is detected as write operation
    When I check if "SAVEPOINT my_savepoint" is a write
    Then is_write_operation should return true

  Scenario: RELEASE is detected as write operation
    When I check if "RELEASE SAVEPOINT my_savepoint" is a write
    Then is_write_operation should return true

  Scenario: ROLLBACK is detected as write operation
    When I check if "ROLLBACK TO SAVEPOINT my_savepoint" is a write
    Then is_write_operation should return true

  # ---------------------------------------------------------------------------
  # PRAGMA Statements - Conditional Detection
  # ---------------------------------------------------------------------------

  Scenario: PRAGMA with assignment is detected as write operation
    When I check if "PRAGMA user_version = 1" is a write
    Then is_write_operation should return true

  Scenario: PRAGMA without assignment is NOT detected as write
    When I check if "PRAGMA journal_mode" is a write
    Then is_write_operation should return false

  Scenario: PRAGMA query is NOT detected as write
    When I check if "PRAGMA table_info(users)" is a write
    Then is_write_operation should return false

  # ---------------------------------------------------------------------------
  # SELECT Statements - Not Write Operations
  # ---------------------------------------------------------------------------

  Scenario: Simple SELECT is NOT detected as write
    When I check if "SELECT * FROM users" is a write
    Then is_write_operation should return false

  Scenario: SELECT with JOIN is NOT detected as write
    When I check if "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id" is a write
    Then is_write_operation should return false

  Scenario: SELECT with subquery is NOT detected as write
    When I check if "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)" is a write
    Then is_write_operation should return false

  # ---------------------------------------------------------------------------
  # SQL Comment Handling
  # ---------------------------------------------------------------------------

  Scenario: Write keyword after block comment is detected
    When I check if "/* comment */ INSERT INTO users (name) VALUES ('test')" is a write
    Then is_write_operation should return true

  Scenario: Write keyword after line comment is detected
    When I check SQL with line comment followed by INSERT
    Then is_write_operation should return true

  Scenario: SELECT after block comment is NOT detected as write
    When I check if "/* comment */ SELECT * FROM users" is a write
    Then is_write_operation should return false

  # ---------------------------------------------------------------------------
  # CTE (Common Table Expression) Patterns
  # ---------------------------------------------------------------------------

  Scenario: CTE with INSERT in main query is detected as write
    When I check if "WITH cte AS (SELECT 1) INSERT INTO users SELECT * FROM cte" is a write
    Then is_write_operation should return true

  Scenario: CTE with UPDATE in main query is detected as write
    When I check if "WITH cte AS (SELECT 1) UPDATE users SET name = 'test'" is a write
    Then is_write_operation should return true

  Scenario: CTE with DELETE in main query is detected as write
    When I check if "WITH cte AS (SELECT 1) DELETE FROM users WHERE id = 1" is a write
    Then is_write_operation should return true

  Scenario: CTE with SELECT only is NOT detected as write
    When I check if "WITH cte AS (SELECT 1) SELECT * FROM cte" is a write
    Then is_write_operation should return false

  # ---------------------------------------------------------------------------
  # False Positive Prevention - Column/Table Names
  # ---------------------------------------------------------------------------

  Scenario: Column named delete_flag is NOT detected as write
    When I check if "SELECT delete_flag FROM users" is a write
    Then is_write_operation should return false

  Scenario: Column named update_count is NOT detected as write
    When I check if "SELECT update_count FROM stats" is a write
    Then is_write_operation should return false

  Scenario: Column named insert_date is NOT detected as write
    When I check if "SELECT insert_date FROM logs" is a write
    Then is_write_operation should return false

  Scenario: CTE alias named UPDATE is NOT detected as write
    When I check if "WITH UPDATE AS (SELECT 1) SELECT * FROM UPDATE" is a write
    Then is_write_operation should return false

  # ---------------------------------------------------------------------------
  # Edge Cases
  # ---------------------------------------------------------------------------

  Scenario: Empty string is NOT detected as write
    When I check an empty SQL string
    Then is_write_operation should return false

  Scenario: Whitespace-only string is NOT detected as write
    When I check if "   " is a write
    Then is_write_operation should return false

  Scenario: Case-insensitive detection works
    When I check if "insert into users (name) values ('test')" is a write
    Then is_write_operation should return true
