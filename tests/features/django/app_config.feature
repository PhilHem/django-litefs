# @bdd-decomposed: 2025-12-27 status=implemented
Feature: LiteFS Django App Configuration
  As a developer
  I want litefs_django to integrate cleanly with Django's app system
  So that I can add LiteFS support with minimal configuration

  The litefs_django app integrates with Django via AppConfig. When added to
  INSTALLED_APPS, it validates configuration at startup and provides sensible
  defaults for common deployment scenarios.

  TRA Namespace: Adapter.Django.AppConfig

  Background:
    Given a Django project with litefs_django in INSTALLED_APPS

  # ---------------------------------------------------------------------------
  # App Registration
  # ---------------------------------------------------------------------------

  Scenario: App registers successfully with valid LITEFS settings
    Given LITEFS settings are configured with:
      | field       | value       |
      | mount_path  | /mnt/litefs |
      | data_path   | /var/lib/litefs |
    When Django initializes the application
    Then the LiteFSDjangoConfig.ready() hook should complete without error
    And LiteFS settings should be available via get_litefs_settings()

  Scenario: App registers successfully without LITEFS settings
    Given no LITEFS settings dict is defined in Django settings
    When Django initializes the application
    Then the app should register without error
    And get_litefs_settings() should return None

  Scenario: App emits debug log when LiteFS not configured
    Given no LITEFS settings dict is defined in Django settings
    When Django initializes the application
    Then a debug message should be logged containing "LiteFS not configured"

  # ---------------------------------------------------------------------------
  # Settings Validation at Startup
  # ---------------------------------------------------------------------------

  Scenario: App validates LITEFS settings on startup
    Given LITEFS settings are configured with:
      | field       | value       |
      | mount_path  | /mnt/litefs |
    When Django initializes the application
    Then LiteFSSettings domain object should be created
    And validation should be delegated to core domain

  Scenario: App raises error for invalid LITEFS settings
    Given LITEFS settings are configured with:
      | field       | value         |
      | mount_path  | relative/path |
    When Django initializes the application
    Then a LiteFSConfigError should be raised
    And the error message should contain "absolute path"
    And Django should fail to start

  Scenario: App raises error for invalid leader_election value
    Given LITEFS settings are configured with:
      | field           | value       |
      | mount_path      | /mnt/litefs |
      | leader_election | invalid     |
    When Django initializes the application
    Then a LiteFSConfigError should be raised
    And the error message should contain "leader_election"

  # ---------------------------------------------------------------------------
  # Database Backend Detection
  # ---------------------------------------------------------------------------

  Scenario: App detects litefs database backend is configured
    Given DATABASE is configured with:
      | setting | value                            |
      | ENGINE  | litefs_django.db.backends.litefs |
      | NAME    | /mnt/litefs/db.sqlite3           |
    When Django initializes the application
    Then the app should recognize LiteFS backend is in use

  Scenario: App warns when LITEFS settings exist but backend not configured
    Given LITEFS settings are fully configured
    And DATABASE ENGINE is "django.db.backends.sqlite3"
    When Django runs system checks
    Then a warning should be emitted with id "litefs_django.W001"
    And the warning should suggest using "litefs_django.db.backends.litefs"

  # ---------------------------------------------------------------------------
  # Settings Access API
  # ---------------------------------------------------------------------------

  Scenario: Settings accessible via get_litefs_settings function
    Given LITEFS settings are configured with:
      | field       | value       |
      | mount_path  | /mnt/litefs |
    When I call get_litefs_settings()
    Then it should return a LiteFSSettings instance
    And the mount_path should be "/mnt/litefs"

  Scenario: Settings cached after first access
    Given LITEFS settings are configured
    When I call get_litefs_settings() twice
    Then both calls should return the same instance
    And Django settings should only be read once
