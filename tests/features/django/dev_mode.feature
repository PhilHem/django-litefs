# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: LiteFS Django Development Mode
  As a developer
  I want to disable LiteFS features during local development
  So that I can develop without running LiteFS infrastructure

  Development mode allows developers to work locally with standard SQLite
  while the same codebase uses LiteFS in production. When LITEFS.enabled
  is False, the database backend behaves as standard Django SQLite.

  TRA Namespace: Adapter.Django.DevMode

  # ---------------------------------------------------------------------------
  # Enabling/Disabling LiteFS
  # ---------------------------------------------------------------------------

  Scenario: LiteFS disabled via settings
    Given a Django project with LITEFS settings:
      | field   | value |
      | enabled | False |
    When the database backend initializes
    Then LiteFS-specific features should be disabled
    And the backend should delegate to standard SQLite

  Scenario: LiteFS enabled by default when settings present
    Given a Django project with LITEFS settings:
      | field      | value       |
      | mount_path | /mnt/litefs |
    And "enabled" is not specified
    When the database backend initializes
    Then LiteFS features should be enabled

  Scenario: LiteFS disabled when LITEFS settings missing entirely
    Given a Django project with no LITEFS settings dict
    And DATABASE ENGINE is "litefs_django.db.backends.litefs"
    When the database backend initializes
    Then the backend should behave as standard SQLite
    And no LiteFS validation should occur

  # ---------------------------------------------------------------------------
  # Development Mode Behavior
  # ---------------------------------------------------------------------------

  Scenario: No mount path validation in dev mode
    Given a Django project with LITEFS.enabled = False
    And DATABASE OPTIONS has litefs_mount_path "/nonexistent/path"
    When I create a database connection
    Then the connection should succeed
    And no mount path check should occur

  Scenario: No primary/replica check in dev mode
    Given a Django project with LITEFS.enabled = False
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the query should execute successfully
    And no is_primary() check should occur

  Scenario: No split-brain check in dev mode
    Given a Django project with LITEFS.enabled = False
    When I execute "INSERT INTO users (name) VALUES ('test')"
    Then the query should execute successfully
    And no split-brain detection should occur

  Scenario: All Django ORM operations work in dev mode
    Given a Django project with LITEFS.enabled = False
    When I perform standard Django ORM operations:
      | operation | model |
      | create    | User  |
      | read      | User  |
      | update    | User  |
      | delete    | User  |
    Then all operations should succeed

  # ---------------------------------------------------------------------------
  # Binary Independence
  # ---------------------------------------------------------------------------

  Scenario: Dev mode works without litefs binary installed
    Given a Django project with LITEFS.enabled = False
    And the litefs binary is not in PATH
    When the Django application starts
    Then no error should be raised
    And database operations should work normally

  Scenario: Dev mode works without FUSE available
    Given a Django project with LITEFS.enabled = False
    And FUSE is not available on the system
    When the Django application starts
    Then no error should be raised
    And database operations should work normally

  # ---------------------------------------------------------------------------
  # Environment-Based Configuration
  # ---------------------------------------------------------------------------

  Scenario: Dev mode controlled via environment variable
    Given a Django project with LITEFS settings:
      | field   | value                       |
      | enabled | ${LITEFS_ENABLED:False}     |
    And environment variable LITEFS_ENABLED is not set
    When the database backend initializes
    Then LiteFS should be disabled

  Scenario: Production enables LiteFS via environment
    Given a Django project with LITEFS settings:
      | field   | value                       |
      | enabled | ${LITEFS_ENABLED:False}     |
    And environment variable LITEFS_ENABLED is "true"
    When the database backend initializes
    Then LiteFS should be enabled

  # ---------------------------------------------------------------------------
  # Switching Modes
  # ---------------------------------------------------------------------------

  Scenario: Same codebase works in both modes
    Given a Django project configured for LiteFS
    When LITEFS.enabled is toggled between True and False
    Then the application should work correctly in both modes
    And no code changes should be required
