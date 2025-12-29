# @bdd-decomposed: 2025-12-29 epic=django-litefs-e2r status=complete
Feature: Quick Start Installation
  As a developer
  I want to install litefs-django from PyPI and get it working
  So that I can add distributed SQLite to my Django app with minimal effort

  The installation experience should be seamless:
  1. pip install litefs-django
  2. Add to INSTALLED_APPS and configure DATABASES
  3. Run manage.py litefs_check to verify setup
  4. LiteFS binary auto-downloads on first use if not present

  TRA Namespace: Core.Installation

  # ---------------------------------------------------------------------------
  # PyPI Installation
  # ---------------------------------------------------------------------------

  Scenario: Package installs from PyPI with all dependencies
    When I run "pip install litefs-django"
    Then the installation should succeed
    And litefs-py core package should be installed as dependency
    And no LiteFS binary should be downloaded yet

  Scenario: Package works with pip, pipx, uv, and poetry
    When I install litefs-django using "<installer>"
    Then the installation should succeed

    Examples:
      | installer |
      | pip       |
      | uv        |
      | poetry    |

  # ---------------------------------------------------------------------------
  # Binary Auto-Download
  # ---------------------------------------------------------------------------

  Scenario: LiteFS binary auto-downloads on first use
    Given litefs-django is installed
    And the LiteFS binary is not present
    When I run "python manage.py litefs_check"
    Then the LiteFS binary should be downloaded automatically
    And the binary should be placed in a user-writable location
    And the download should show progress feedback

  Scenario: Binary download detects correct platform
    Given litefs-django is installed
    And the LiteFS binary is not present
    When binary download is triggered
    Then the correct binary for the current platform should be selected
    And supported platforms should include:
      | os     | arch   |
      | linux  | amd64  |
      | linux  | arm64  |
      | darwin | amd64  |
      | darwin | arm64  |

  Scenario: Binary is cached after first download
    Given the LiteFS binary was previously downloaded
    When I run "python manage.py litefs_check"
    Then no download should occur
    And the cached binary should be used

  Scenario: Binary version matches package compatibility
    Given litefs-django is installed
    When the LiteFS binary is downloaded
    Then the binary version should be compatible with litefs-py
    And the version should be recorded for future checks

  Scenario: Explicit binary download command available
    Given litefs-django is installed
    When I run "python manage.py litefs_download"
    Then the LiteFS binary should be downloaded
    And the command should report the download location
    And the command should verify the binary works

  # ---------------------------------------------------------------------------
  # Download Failure Handling
  # ---------------------------------------------------------------------------

  Scenario: Clear error when download fails due to network
    Given litefs-django is installed
    And the LiteFS binary is not present
    And network is unavailable
    When I run "python manage.py litefs_check"
    Then an error should indicate download failed
    And the error should suggest manual installation steps
    And the error should include the download URL

  Scenario: Clear error on unsupported platform
    Given litefs-django is installed
    And the current platform is not supported
    When binary download is triggered
    Then an error should indicate the platform is unsupported
    And the error should list supported platforms
    And the error should suggest Docker as alternative

  Scenario: Corrupted download is detected and retried
    Given litefs-django is installed
    And a previous download was corrupted
    When I run "python manage.py litefs_check"
    Then the corrupted binary should be detected
    And a fresh download should be attempted
    And the checksum should be verified

  # ---------------------------------------------------------------------------
  # Minimal Configuration
  # ---------------------------------------------------------------------------

  Scenario: Minimal settings get LiteFS working
    Given litefs-django is installed
    And Django settings contain only:
      """
      INSTALLED_APPS = [..., 'litefs_django']

      DATABASES = {
          'default': {
              'ENGINE': 'litefs_django.db.backends.litefs',
              'NAME': '/mnt/litefs/db.sqlite3',
              'OPTIONS': {
                  'litefs_mount_path': '/mnt/litefs',
              }
          }
      }
      """
    When I run "python manage.py litefs_check"
    Then all checks should pass
    And LiteFS should be ready to use

  Scenario: Sensible defaults reduce required configuration
    Given litefs-django is installed
    And DATABASE NAME is "/mnt/litefs/db.sqlite3"
    And no explicit litefs_mount_path is set
    When the database backend initializes
    Then mount_path should be inferred from DATABASE NAME parent directory
    And a debug message should confirm the inferred path

  # ---------------------------------------------------------------------------
  # Setup Verification
  # ---------------------------------------------------------------------------

  Scenario: litefs_check verifies complete installation
    Given litefs-django is properly configured
    When I run "python manage.py litefs_check"
    Then the output should verify:
      | check                  | status |
      | Package installed      | OK     |
      | Binary available       | OK     |
      | Binary version         | OK     |
      | Settings valid         | OK     |
      | Mount path accessible  | OK     |
      | Database backend       | OK     |

  Scenario: litefs_check downloads binary if missing
    Given litefs-django is properly configured
    And the LiteFS binary is not present
    When I run "python manage.py litefs_check"
    Then the binary should be downloaded first
    And then all checks should run
    And the final status should be OK

  Scenario: litefs_check reports all issues with fix suggestions
    Given litefs-django is installed with issues:
      | issue                    |
      | Binary not found         |
      | Mount path not accessible|
    When I run "python manage.py litefs_check"
    Then each issue should have a suggested fix
    And fixes should be actionable commands when possible

  # ---------------------------------------------------------------------------
  # Development Mode (No Binary Required)
  # ---------------------------------------------------------------------------

  Scenario: Dev mode works without binary download
    Given litefs-django is installed
    And LITEFS settings have enabled=False
    When the Django application starts
    Then no binary download should be triggered
    And the app should work with standard SQLite

  Scenario: litefs_check skips binary check in dev mode
    Given litefs-django is installed
    And LITEFS settings have enabled=False
    When I run "python manage.py litefs_check"
    Then binary check should be skipped
    And output should indicate "LiteFS disabled (dev mode)"

  # ---------------------------------------------------------------------------
  # Binary Location Options
  # ---------------------------------------------------------------------------

  Scenario: Binary installed to user cache by default
    Given litefs-django is installed
    When the binary is downloaded
    Then it should be placed in the user cache directory
    And the location should follow platform conventions:
      | platform | location                          |
      | linux    | ~/.cache/litefs/bin/litefs        |
      | darwin   | ~/Library/Caches/litefs/bin/litefs|

  Scenario: Binary location can be overridden
    Given litefs-django is installed
    And environment variable LITEFS_BINARY_PATH is set to "/custom/path/litefs"
    When the binary is downloaded
    Then it should be placed at "/custom/path/litefs"

  Scenario: System-installed binary is detected and used
    Given litefs-django is installed
    And litefs binary exists in system PATH
    When I run "python manage.py litefs_check"
    Then the system binary should be detected
    And no download should occur
    And output should indicate "Using system LiteFS"
