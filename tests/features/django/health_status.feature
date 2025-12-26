# @bdd-decomposed: 2025-12-26 epic=django-litefs-d9q status=complete
Feature: Health Status Endpoint for Operators
  As an operator or monitoring system
  I want a detailed health status endpoint
  So that I can diagnose cluster state and troubleshoot issues

  The health status endpoint returns comprehensive JSON with all health details.
  Unlike probes (binary ready/not-ready), this endpoint provides rich diagnostic
  information for human operators and monitoring dashboards.

  This feature covers the detailed health endpoint used by:
  - Operators debugging cluster issues
  - Monitoring systems (Prometheus, Datadog, etc.)
  - Admin dashboards

  TRA Namespace: Contract.HealthStatus

  # ---------------------------------------------------------------------------
  # Detailed Health Response
  # ---------------------------------------------------------------------------
  # Returns comprehensive health information including node state, health status,
  # primary/replica role, and error details when applicable.

  Scenario: Health endpoint returns complete status for primary
    Given the node is the primary
    And the node health status is "healthy"
    When I request the health endpoint
    Then the response status should be 200
    And the response should include "is_primary" as true
    And the response should include "health_status" as "healthy"
    And the response should include "node_state" as "PRIMARY"
    And the response should include "is_ready" as true

  Scenario: Health endpoint returns complete status for replica
    Given the node is a replica
    And the node health status is "healthy"
    When I request the health endpoint
    Then the response status should be 200
    And the response should include "is_primary" as false
    And the response should include "health_status" as "healthy"
    And the response should include "node_state" as "REPLICA"

  Scenario: Health endpoint includes error details when LiteFS not running
    Given LiteFS is not running on the node
    When I request the health endpoint
    Then the response status should be 503
    And the response should include "error"
    And the response should include "health_status" as "unhealthy"

  Scenario: Health endpoint returns degraded status with details
    Given the node is the primary
    And the node health status is "degraded"
    When I request the health endpoint
    Then the response status should be 200
    And the response should include "health_status" as "degraded"
    And the response should include "is_primary" as true
    And the response should include "is_ready" as false
