# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: LiteFS Django Management Commands
  As a Django application developer
  I want management commands to validate and diagnose LiteFS setup
  So that I can quickly identify and fix configuration issues

  The litefs_django package provides management commands for setup validation
  and diagnostics. These commands help developers verify their configuration
  before deployment and troubleshoot issues in production.

  TRA Namespace: Adapter.Django.ManagementCommands

  # ---------------------------------------------------------------------------
  # litefs_check Command - Setup Validation
  # ---------------------------------------------------------------------------

  Scenario: litefs_check validates complete setup
    Given a Django project with litefs_django installed
    And LITEFS settings are correctly configured
    And DATABASE backend is litefs_django.db.backends.litefs
    And the LiteFS mount path exists and is accessible
    When I run "python manage.py litefs_check"
    Then the command should exit with code 0
    And the output should show all checks passed

  Scenario: litefs_check reports missing LITEFS settings
    Given a Django project with litefs_django installed
    And no LITEFS settings are configured
    When I run "python manage.py litefs_check"
    Then the command should exit with code 1
    And the output should indicate "LITEFS settings not configured"
    And the output should suggest adding LITEFS dict to settings

  Scenario: litefs_check reports wrong database backend
    Given a Django project with litefs_django installed
    And LITEFS settings are configured
    And DATABASE ENGINE is "django.db.backends.sqlite3"
    When I run "python manage.py litefs_check"
    Then the command should exit with code 1
    And the output should indicate "Database backend mismatch"
    And the output should suggest using litefs backend

  Scenario: litefs_check reports inaccessible mount path
    Given a Django project with litefs_django installed
    And LITEFS settings have mount_path "/mnt/litefs"
    And the path "/mnt/litefs" does not exist
    When I run "python manage.py litefs_check"
    Then the command should exit with code 1
    And the output should indicate "Mount path not accessible"
    And the output should suggest checking LiteFS is running

  Scenario: litefs_check reports all issues at once
    Given a Django project with multiple configuration issues:
      | issue                    |
      | wrong database backend   |
      | mount path not accessible|
    When I run "python manage.py litefs_check"
    Then the output should list all issues
    And each issue should have a suggested fix
    And the command should exit with code 1

  # ---------------------------------------------------------------------------
  # litefs_check Command - Verbosity Levels
  # ---------------------------------------------------------------------------

  Scenario: litefs_check with verbosity 0 shows only errors
    Given a Django project with configuration issues
    When I run "python manage.py litefs_check -v 0"
    Then only error messages should be displayed
    And no informational output should appear

  Scenario: litefs_check with verbosity 2 shows detailed info
    Given a Django project with correct configuration
    When I run "python manage.py litefs_check -v 2"
    Then detailed configuration values should be displayed
    And each check step should be shown

  # ---------------------------------------------------------------------------
  # litefs_status Command - Runtime Status
  # ---------------------------------------------------------------------------

  Scenario: litefs_status shows current node state
    Given a Django project with LiteFS running
    When I run "python manage.py litefs_status"
    Then the output should show:
      | field        | description           |
      | node_role    | primary or replica    |
      | mount_path   | configured mount path |
      | health       | healthy/degraded/unhealthy |

  Scenario: litefs_status shows primary when node is primary
    Given a Django project with LiteFS running
    And the current node is the primary
    When I run "python manage.py litefs_status"
    Then the output should indicate "Role: primary"

  Scenario: litefs_status shows replica when node is replica
    Given a Django project with LiteFS running
    And the current node is a replica
    When I run "python manage.py litefs_status"
    Then the output should indicate "Role: replica"

  Scenario: litefs_status reports when LiteFS not running
    Given a Django project with LiteFS configured
    And the LiteFS mount path does not exist
    When I run "python manage.py litefs_status"
    Then the command should exit with code 1
    And the output should indicate "LiteFS not running"

  # ---------------------------------------------------------------------------
  # JSON Output Format
  # ---------------------------------------------------------------------------

  Scenario: litefs_check supports JSON output
    Given a Django project with correct configuration
    When I run "python manage.py litefs_check --format=json"
    Then the output should be valid JSON
    And the JSON should contain "status" field
    And the JSON should contain "checks" array

  Scenario: litefs_status supports JSON output
    Given a Django project with LiteFS running
    When I run "python manage.py litefs_status --format=json"
    Then the output should be valid JSON
    And the JSON should contain node state information
