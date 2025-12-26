# @bdd-decomposed: 2025-12-26 epic=django-litefs-8oi status=complete
Feature: LiteFS Django Database Backend
  As a Django application developer
  I want a database backend that enforces LiteFS replication constraints
  So that data consistency is maintained across the cluster

  The LiteFS database backend wraps Django's SQLite backend to enforce distributed
  database constraints. It ensures:
  - Write operations only execute on the primary node
  - Writes are blocked during split-brain conditions
  - The LiteFS mount path is validated at connection time
  - Transaction mode is set appropriately for replication

  This backend is the enforcement layer between Django ORM and LiteFS, translating
  distributed system concerns into Django-compatible database errors.

  # ---------------------------------------------------------------------------
  # Backend Configuration - Mount Path Validation
  # ---------------------------------------------------------------------------

  Scenario: Backend validates mount path exists at connection time
    Given a database configuration with mount path "/mnt/litefs"
    And the mount path exists and is accessible
    When I create a database connection
    Then the connection should succeed
    And the mount path should be validated

  Scenario: Backend rejects missing mount path
    Given a database configuration with mount path "/mnt/nonexistent"
    And the mount path does not exist
    When I create a database connection
    Then a configuration error should be raised
    And the error message should contain "mount path"

  Scenario: Backend rejects inaccessible mount path
    Given a database configuration with mount path "/mnt/litefs"
    And the mount path exists but is not accessible
    When I create a database connection
    Then a configuration error should be raised
    And the error message should contain "not accessible"

  Scenario: Backend requires mount path in OPTIONS
    Given a database configuration without litefs_mount_path
    When I create a database connection
    Then a configuration error should be raised
    And the error message should contain "litefs_mount_path is required"

  # ---------------------------------------------------------------------------
  # Backend Configuration - Transaction Mode
  # ---------------------------------------------------------------------------

  Scenario: Backend defaults to IMMEDIATE transaction mode
    Given a database configuration with mount path "/mnt/litefs"
    And no explicit transaction mode is set
    When I create a database connection
    Then the transaction mode should be "IMMEDIATE"

  Scenario: Backend accepts explicit IMMEDIATE transaction mode
    Given a database configuration with:
      | option            | value      |
      | litefs_mount_path | /mnt/litefs|
      | transaction_mode  | IMMEDIATE  |
    When I create a database connection
    Then the transaction mode should be "IMMEDIATE"

  Scenario: Backend accepts EXCLUSIVE transaction mode
    Given a database configuration with:
      | option            | value      |
      | litefs_mount_path | /mnt/litefs|
      | transaction_mode  | EXCLUSIVE  |
    When I create a database connection
    Then the transaction mode should be "EXCLUSIVE"

  Scenario: Backend rejects invalid transaction mode
    Given a database configuration with:
      | option            | value      |
      | litefs_mount_path | /mnt/litefs|
      | transaction_mode  | INVALID    |
    When I create a database connection
    Then a configuration error should be raised
    And the error message should contain "transaction_mode"

  # ---------------------------------------------------------------------------
  # Write Operation Guarding - Primary Detection
  # ---------------------------------------------------------------------------

  Scenario: Write succeeds on primary node
    Given a database connection to the primary node
    And no split-brain condition exists
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the operation should succeed

  Scenario: Write fails on replica node with NotPrimaryError
    Given a database connection to a replica node
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then a NotPrimaryError should be raised
    And the error message should contain "not primary"

  Scenario: UPDATE fails on replica node
    Given a database connection to a replica node
    When I execute "UPDATE users SET name = 'updated' WHERE id = 1"
    Then a NotPrimaryError should be raised

  Scenario: DELETE fails on replica node
    Given a database connection to a replica node
    When I execute "DELETE FROM users WHERE id = 1"
    Then a NotPrimaryError should be raised

  Scenario: CREATE TABLE fails on replica node
    Given a database connection to a replica node
    When I execute "CREATE TABLE test (id INTEGER PRIMARY KEY)"
    Then a NotPrimaryError should be raised

  Scenario: DROP TABLE fails on replica node
    Given a database connection to a replica node
    When I execute "DROP TABLE test"
    Then a NotPrimaryError should be raised

  Scenario: ALTER TABLE fails on replica node
    Given a database connection to a replica node
    When I execute "ALTER TABLE users ADD COLUMN email TEXT"
    Then a NotPrimaryError should be raised

  # ---------------------------------------------------------------------------
  # Write Operation Guarding - Read Operations Allowed
  # ---------------------------------------------------------------------------

  Scenario: SELECT succeeds on replica node
    Given a database connection to a replica node
    When I execute "SELECT * FROM users"
    Then the operation should succeed

  Scenario: SELECT with JOIN succeeds on replica node
    Given a database connection to a replica node
    When I execute "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id"
    Then the operation should succeed

  Scenario: PRAGMA query succeeds on replica node
    Given a database connection to a replica node
    When I execute "PRAGMA table_info(users)"
    Then the operation should succeed

  Scenario: Read succeeds on primary node
    Given a database connection to the primary node
    When I execute "SELECT * FROM users"
    Then the operation should succeed

  # ---------------------------------------------------------------------------
  # Split-Brain Protection
  # ---------------------------------------------------------------------------

  Scenario: Write fails during split-brain with SplitBrainError
    Given a database connection to the primary node
    And a split-brain condition exists with 2 leaders
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then a SplitBrainError should be raised
    And the error message should contain "split-brain"

  Scenario: Split-brain check occurs before primary check
    Given a database connection to a replica node
    And a split-brain condition exists with 2 leaders
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then a SplitBrainError should be raised
    And NotPrimaryError should NOT be raised

  Scenario: Read succeeds during split-brain
    Given a database connection to the primary node
    And a split-brain condition exists with 2 leaders
    When I execute "SELECT * FROM users"
    Then the operation should succeed

  Scenario: Write succeeds when split-brain resolves
    Given a database connection to the primary node
    And no split-brain condition exists
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the operation should succeed

  # ---------------------------------------------------------------------------
  # Cursor Methods - execute()
  # ---------------------------------------------------------------------------

  Scenario: execute() checks primary status for write operations
    Given a database connection to a replica node
    When I call execute with "INSERT INTO users (name) VALUES ('test')"
    Then a NotPrimaryError should be raised

  Scenario: execute() allows read operations on replica
    Given a database connection to a replica node
    When I call execute with "SELECT * FROM users"
    Then the operation should succeed

  Scenario: execute() with parameters checks write status
    Given a database connection to a replica node
    When I call execute with "INSERT INTO users (name) VALUES (?)" and parameters ["test"]
    Then a NotPrimaryError should be raised

  # ---------------------------------------------------------------------------
  # Cursor Methods - executemany()
  # ---------------------------------------------------------------------------

  Scenario: executemany() checks primary status for write operations
    Given a database connection to a replica node
    When I call executemany with "INSERT INTO users (name) VALUES (?)" and [["a"], ["b"]]
    Then a NotPrimaryError should be raised

  Scenario: executemany() allows read operations on replica
    Given a database connection to a replica node
    When I call executemany with "SELECT * FROM users WHERE id = ?" and [[1], [2]]
    Then the operation should succeed

  # ---------------------------------------------------------------------------
  # Cursor Methods - executescript()
  # ---------------------------------------------------------------------------

  Scenario: executescript() checks for any write operation
    Given a database connection to a replica node
    When I call executescript with "SELECT 1; INSERT INTO users (name) VALUES ('test');"
    Then a NotPrimaryError should be raised

  Scenario: executescript() allows read-only scripts on replica
    Given a database connection to a replica node
    When I call executescript with "SELECT 1; SELECT 2; SELECT 3;"
    Then the operation should succeed

  Scenario: executescript() checks split-brain before executing
    Given a database connection to the primary node
    And a split-brain condition exists with 2 leaders
    When I call executescript with "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    Then a SplitBrainError should be raised

  # ---------------------------------------------------------------------------
  # Database Maintenance Operations
  # ---------------------------------------------------------------------------

  Scenario: VACUUM fails on replica node
    Given a database connection to a replica node
    When I execute "VACUUM"
    Then a NotPrimaryError should be raised

  Scenario: REINDEX fails on replica node
    Given a database connection to a replica node
    When I execute "REINDEX"
    Then a NotPrimaryError should be raised

  Scenario: ANALYZE fails on replica node
    Given a database connection to a replica node
    When I execute "ANALYZE"
    Then a NotPrimaryError should be raised

  # ---------------------------------------------------------------------------
  # WAL Mode Enforcement
  # ---------------------------------------------------------------------------

  Scenario: Backend enforces WAL journal mode
    Given a database configuration with mount path "/mnt/litefs"
    When I create a database connection
    Then the journal mode should be "wal"

  Scenario: Attempting to change journal mode is blocked
    Given a database connection to the primary node
    When I execute "PRAGMA journal_mode = DELETE"
    Then either the operation should fail or journal mode should remain "wal"

  # ---------------------------------------------------------------------------
  # Error Message Quality
  # ---------------------------------------------------------------------------

  Scenario: NotPrimaryError includes helpful context
    Given a database connection to a replica node
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the NotPrimaryError message should include:
      | content                          |
      | not primary                      |
      | replica                          |

  Scenario: SplitBrainError includes leader count
    Given a database connection to the primary node
    And a split-brain condition exists with 3 leaders
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the SplitBrainError message should include:
      | content                          |
      | split-brain                      |
      | 3 leaders                        |

  # ---------------------------------------------------------------------------
  # Optional Split-Brain Detection
  # ---------------------------------------------------------------------------

  Scenario: Backend works without split-brain detector configured
    Given a database configuration with mount path "/mnt/litefs"
    And no split-brain detector is configured
    When I create a database connection
    Then the connection should succeed

  Scenario: Write succeeds without split-brain detector on primary
    Given a database connection to the primary node
    And no split-brain detector is configured
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the operation should succeed

  Scenario: Write fails without split-brain detector on replica
    Given a database connection to a replica node
    And no split-brain detector is configured
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then a NotPrimaryError should be raised

  # ---------------------------------------------------------------------------
  # Connection Lifecycle
  # ---------------------------------------------------------------------------

  Scenario: Cursor inherits detectors from connection
    Given a database connection with configured detectors
    When I create a cursor from the connection
    Then the cursor should have the same primary detector
    And the cursor should have the same split-brain detector

  Scenario: Multiple cursors share the same detectors
    Given a database connection with configured detectors
    When I create multiple cursors from the connection
    Then all cursors should use the same detector instances

  # ---------------------------------------------------------------------------
  # Django ORM Integration
  # ---------------------------------------------------------------------------

  Scenario: Django model save fails on replica
    Given a database connection to a replica node
    And a Django model instance
    When I call save() on the model
    Then a NotPrimaryError should be raised

  Scenario: Django model save succeeds on primary
    Given a database connection to the primary node
    And no split-brain condition exists
    And a Django model instance
    When I call save() on the model
    Then the operation should succeed

  Scenario: Django queryset update fails on replica
    Given a database connection to a replica node
    When I call queryset.update(name='new')
    Then a NotPrimaryError should be raised

  Scenario: Django queryset delete fails on replica
    Given a database connection to a replica node
    When I call queryset.delete()
    Then a NotPrimaryError should be raised

  Scenario: Django queryset filter succeeds on replica
    Given a database connection to a replica node
    When I call queryset.filter(name='test')
    Then the operation should succeed
