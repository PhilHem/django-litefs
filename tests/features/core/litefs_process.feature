# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: LiteFS Process Detection
  As a developer
  I want to detect if LiteFS is running and query its state
  So that my application can respond appropriately to LiteFS availability

  The litefs-py library interacts with the LiteFS binary through:
  - Mount path detection (is LiteFS running?)
  - Primary file reading (who is the primary?)
  - Primary URL discovery (where to forward writes?)

  This feature covers the library's interface to the LiteFS process,
  NOT cluster management (which is LiteFS binary's responsibility).

  TRA Namespace: Core.Process

  # ---------------------------------------------------------------------------
  # LiteFS Mount Detection
  # ---------------------------------------------------------------------------

  Scenario: LiteFS detected when mount path exists
    Given LiteFS is configured with mount_path "/mnt/litefs"
    And the directory "/mnt/litefs" exists
    When I check if LiteFS is running
    Then the result should be true

  Scenario: LiteFS not detected when mount path missing
    Given LiteFS is configured with mount_path "/mnt/litefs"
    And the directory "/mnt/litefs" does not exist
    When I check if LiteFS is running
    Then the result should be false

  Scenario: LiteFSNotRunningError raised for operations requiring LiteFS
    Given LiteFS is configured with mount_path "/mnt/litefs"
    And the directory "/mnt/litefs" does not exist
    When I attempt to check primary status
    Then a LiteFSNotRunningError should be raised
    And the error message should contain "mount path"
    And the error message should contain "/mnt/litefs"

  # ---------------------------------------------------------------------------
  # Primary Node Detection
  # ---------------------------------------------------------------------------

  Scenario: Node is primary when .primary file exists
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" exists
    When I check if this node is primary
    Then the result should be true

  Scenario: Node is replica when .primary file missing
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" does not exist
    When I check if this node is primary
    Then the result should be false

  Scenario: Primary check is idempotent
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" exists
    When I check if this node is primary multiple times
    Then all results should be true
    And no side effects should occur

  # ---------------------------------------------------------------------------
  # Primary URL Discovery
  # ---------------------------------------------------------------------------

  Scenario: Primary URL read from .primary file content
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" contains "primary.local:8080"
    When I get the primary URL
    Then the result should be "primary.local:8080"

  Scenario: Primary URL unavailable on primary node
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" exists but is empty
    When I get the primary URL
    Then the result should indicate this node is primary

  Scenario: Primary URL unavailable when no primary elected
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" does not exist
    When I get the primary URL
    Then the result should be None
    And no error should be raised

  # ---------------------------------------------------------------------------
  # Mount Path Validation
  # ---------------------------------------------------------------------------

  Scenario: Mount path must be absolute
    Given LiteFS settings with mount_path "relative/path"
    When the settings are validated
    Then a LiteFSConfigError should be raised
    And the error message should contain "absolute path"

  Scenario: Mount path validated at settings creation
    Given LiteFS settings with mount_path "/mnt/litefs"
    When the settings are created
    Then validation should pass
    And the mount_path should be stored as-is

  # ---------------------------------------------------------------------------
  # Caching Behavior
  # ---------------------------------------------------------------------------

  Scenario: Primary status not cached by default
    Given LiteFS mount path "/mnt/litefs" exists
    And the file "/mnt/litefs/.primary" exists
    When I check if this node is primary
    And the ".primary" file is removed
    And I check if this node is primary again
    Then the second result should be false

  Scenario: Primary status can be cached with TTL
    Given LiteFS mount path "/mnt/litefs" exists
    And primary status caching is enabled with TTL 5 seconds
    And the file "/mnt/litefs/.primary" exists
    When I check if this node is primary
    And the ".primary" file is removed within TTL
    And I check if this node is primary again
    Then the second result should still be true
