# @bdd-decomposed: 2025-12-26 epic=django-litefs-8oi status=complete
Feature: LiteFS Django Database Backend
  As a developer
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

  TRA Namespace: Adapter.Database.LiteFS

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

  Scenario: Backend rejects invalid transaction mode
    Given a database configuration with:
      | option            | value      |
      | litefs_mount_path | /mnt/litefs|
      | transaction_mode  | INVALID    |
    When I create a database connection
    Then a configuration error should be raised
    And the error message should contain "transaction_mode"

  # ---------------------------------------------------------------------------
  # Write Operation Guarding
  # ---------------------------------------------------------------------------
  # Note: SQL classification (INSERT vs SELECT) is tested in core/sql_detection.feature.
  # These scenarios test OUR guard logic, not SQLDetector's classification.

  Scenario: Write succeeds on primary node
    Given a database connection to the primary node
    And no split-brain condition exists
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the operation should succeed

  Scenario Outline: Write operations fail on replica with NotPrimaryError
    Given a database connection to a replica node
    When I execute "<sql>"
    Then a NotPrimaryError should be raised

    Examples:
      | sql                                              |
      | INSERT INTO users (name) VALUES ('test')         |
      | UPDATE users SET name = 'updated' WHERE id = 1   |
      | DELETE FROM users WHERE id = 1                   |
      | CREATE TABLE test (id INTEGER PRIMARY KEY)       |
      | DROP TABLE test                                  |
      | ALTER TABLE users ADD COLUMN email TEXT          |

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
  # Cursor Methods - executescript()
  # ---------------------------------------------------------------------------
  # executescript is special: it takes multiple statements and must check ALL
  # before executing any. This differs from execute()/executemany() single-check.

  Scenario: executescript() checks for any write operation
    Given a database connection to a replica node
    When I call executescript with "SELECT 1; INSERT INTO users (name) VALUES ('test');"
    Then a NotPrimaryError should be raised

  Scenario: executescript() checks split-brain before executing
    Given a database connection to the primary node
    And a split-brain condition exists with 2 leaders
    When I call executescript with "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    Then a SplitBrainError should be raised

  # ---------------------------------------------------------------------------
  # WAL Mode Enforcement
  # ---------------------------------------------------------------------------

  Scenario: Backend enforces WAL journal mode
    Given a database configuration with mount path "/mnt/litefs"
    When I create a database connection
    Then the journal mode should be "wal"

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
