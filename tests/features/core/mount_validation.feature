# @bdd-decomposed: 2025-12-26 status=implemented
Feature: Mount Path Validation
  Mount paths are validated to catch configuration errors early.
  This ensures runtime issues are clearly reported with actionable messages.

  The MountValidator ensures mount paths are valid before LiteFS operations.
  Validation happens in two phases:
  1. Configuration-time: Path must be absolute (prevents relative path mistakes)
  2. Runtime: Path must exist (indicates LiteFS is running and mounted)

  Different exceptions distinguish between these failure modes:
  - LiteFSConfigError: Configuration problem (fix your settings)
  - LiteFSNotRunningError: Infrastructure problem (start LiteFS or check FUSE mount)

  # ---------------------------------------------------------------------------
  # Configuration Validation - Absolute Path Required
  # ---------------------------------------------------------------------------

  Scenario: Relative path is rejected
    Given a mount path "litefs"
    When I validate the mount path
    Then a LiteFSConfigError should be raised
    And the error message should contain "absolute"

  Scenario: Dot-relative path is rejected
    Given a mount path "./mnt/litefs"
    When I validate the mount path
    Then a LiteFSConfigError should be raised
    And the error message should contain "absolute"

  # ---------------------------------------------------------------------------
  # Runtime Validation - Path Existence
  # ---------------------------------------------------------------------------

  Scenario: Existing path is valid
    Given a mount path that exists on the filesystem
    When I validate the mount path
    Then validation should succeed

  Scenario: Non-existent path raises LiteFSNotRunningError
    Given a mount path "/nonexistent/litefs/path"
    And the path does not exist on the filesystem
    When I validate the mount path
    Then a LiteFSNotRunningError should be raised
    And the error message should contain "does not exist"
    And the error message should contain "LiteFS may not be running"

  # ---------------------------------------------------------------------------
  # Error Message Clarity
  # ---------------------------------------------------------------------------

  Scenario: Config error includes the invalid path
    Given a mount path "relative/path"
    When I validate the mount path
    Then a LiteFSConfigError should be raised
    And the error message should contain "relative/path"

  Scenario: Runtime error includes the missing path
    Given a mount path "/missing/litefs/mount"
    And the path does not exist on the filesystem
    When I validate the mount path
    Then a LiteFSNotRunningError should be raised
    And the error message should contain "/missing/litefs/mount"
