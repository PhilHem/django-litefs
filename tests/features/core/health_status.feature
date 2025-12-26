# @bdd-decomposed: 2025-12-26 status=implemented
Feature: Health Status Determination
  As a LiteFS node
  I need to report my health status accurately
  So that load balancers and operators can make routing and maintenance decisions

  The HealthChecker use case determines node health using a priority hierarchy:
  1. unhealthy flag (highest priority - overrides all)
  2. degraded flag (medium priority)
  3. healthy (default state)

  The HealthStatus value object is an immutable domain primitive that validates
  health state values and can be used as dictionary keys or in sets.

  # ---------------------------------------------------------------------------
  # HealthChecker Use Case - Priority Hierarchy
  # ---------------------------------------------------------------------------

  Scenario: Node is healthy by default
    Given a health checker with no flags set
    When I check the health status
    Then the health status should be "healthy"

  Scenario: Node is degraded when degraded flag is set
    Given a health checker with degraded flag set to true
    When I check the health status
    Then the health status should be "degraded"

  Scenario: Node is unhealthy when unhealthy flag is set
    Given a health checker with unhealthy flag set to true
    When I check the health status
    Then the health status should be "unhealthy"

  Scenario: Unhealthy takes precedence over degraded
    Given a health checker with degraded flag set to true
    And the unhealthy flag is also set to true
    When I check the health status
    Then the health status should be "unhealthy"

  Scenario: Degraded takes precedence over healthy
    Given a health checker with degraded flag set to true
    And the unhealthy flag is set to false
    When I check the health status
    Then the health status should be "degraded"

  # ---------------------------------------------------------------------------
  # HealthStatus Value Object - Validation
  # ---------------------------------------------------------------------------

  Scenario: HealthStatus rejects invalid state values
    When I create a HealthStatus with state "invalid"
    Then a LiteFSConfigError should be raised
    And the error message should contain "health state must be one of"

  Scenario: HealthStatus accepts healthy state
    When I create a HealthStatus with state "healthy"
    Then the HealthStatus should be valid

  Scenario: HealthStatus accepts degraded state
    When I create a HealthStatus with state "degraded"
    Then the HealthStatus should be valid

  Scenario: HealthStatus accepts unhealthy state
    When I create a HealthStatus with state "unhealthy"
    Then the HealthStatus should be valid

  # ---------------------------------------------------------------------------
  # HealthStatus Value Object - Immutability
  # ---------------------------------------------------------------------------

  Scenario: HealthStatus is immutable
    Given a HealthStatus with state "healthy"
    When I attempt to modify the state
    Then a FrozenInstanceError should be raised
