# @bdd-decomposed: 2025-12-26 epic=django-litefs-yhj status=complete
Feature: Health Probes for Kubernetes and Load Balancers
  As an operator
  I want liveness and readiness probe endpoints
  So that automated systems can make routing and lifecycle decisions

  Health probes return binary ready/not-ready signals for automated systems.
  Liveness determines pod restarts. Readiness determines traffic routing.

  This feature covers the probe endpoints used by:
  - Kubernetes liveness probes (pod restart decisions)
  - Kubernetes readiness probes (traffic routing)
  - Load balancers (primary/replica routing)

  TRA Namespace: Contract.HealthProbe

  # ---------------------------------------------------------------------------
  # Liveness Probe - Is the node alive?
  # ---------------------------------------------------------------------------
  # Used by Kubernetes to decide whether to restart the pod.
  # Should only fail if the process is fundamentally broken.

  Scenario: Liveness returns 200 when LiteFS is running
    Given LiteFS is running on the node
    When I request the liveness endpoint
    Then the response status should be 200
    And the response should include "is_live" as true

  Scenario: Liveness returns 503 when LiteFS is not running
    Given LiteFS is not running on the node
    When I request the liveness endpoint
    Then the response status should be 503
    And the response should include "is_live" as false
    And the response should include an error message

  Scenario: Liveness returns 200 even when node is degraded
    Given LiteFS is running on the node
    And the node health status is "degraded"
    When I request the liveness endpoint
    Then the response status should be 200
    And the response should include "is_live" as true

  # ---------------------------------------------------------------------------
  # Readiness Probe - Can the node accept traffic?
  # ---------------------------------------------------------------------------
  # Used by Kubernetes and load balancers to route traffic.
  # Primary nodes must be healthy to accept writes.
  # Replica nodes can tolerate degradation for reads.

  Scenario: Readiness returns 200 for healthy primary
    Given the node is the primary
    And the node health status is "healthy"
    When I request the readiness endpoint
    Then the response status should be 200
    And the response should include "is_ready" as true
    And the response should include "can_accept_writes" as true

  Scenario: Readiness returns 503 for degraded primary
    Given the node is the primary
    And the node health status is "degraded"
    When I request the readiness endpoint
    Then the response status should be 503
    And the response should include "is_ready" as false
    And the response should include "can_accept_writes" as false

  Scenario: Readiness returns 503 for unhealthy primary
    Given the node is the primary
    And the node health status is "unhealthy"
    When I request the readiness endpoint
    Then the response status should be 503
    And the response should include "is_ready" as false

  Scenario: Readiness returns 200 for healthy replica
    Given the node is a replica
    And the node health status is "healthy"
    When I request the readiness endpoint
    Then the response status should be 200
    And the response should include "is_ready" as true
    And the response should include "can_accept_writes" as false

  Scenario: Readiness returns 200 for degraded replica
    Given the node is a replica
    And the node health status is "degraded"
    When I request the readiness endpoint
    Then the response status should be 200
    And the response should include "is_ready" as true
    And the response should include "can_accept_writes" as false

  Scenario: Readiness returns 503 for unhealthy replica
    Given the node is a replica
    And the node health status is "unhealthy"
    When I request the readiness endpoint
    Then the response status should be 503
    And the response should include "is_ready" as false

  Scenario: Readiness returns 503 when LiteFS is not running
    Given LiteFS is not running on the node
    When I request the readiness endpoint
    Then the response status should be 503
    And the response should include "is_ready" as false

  # ---------------------------------------------------------------------------
  # Split-Brain Detection in Readiness
  # ---------------------------------------------------------------------------
  # Split-brain occurs when multiple nodes claim leadership.
  # Readiness must fail to prevent routing to conflicting primaries.

  Scenario: Readiness returns 503 when split-brain detected
    Given Raft leader election is configured
    And multiple nodes claim leadership
    When I request the readiness endpoint
    Then the response status should be 503
    And the response should include "split_brain_detected" as true
    And the response should include the leader node IDs

  Scenario: Readiness returns 200 with single leader
    Given Raft leader election is configured
    And exactly one node is the leader
    When I request the readiness endpoint
    Then the response status should be 200
    And the response should include "split_brain_detected" as false

  Scenario: Static leader mode skips split-brain detection
    Given static leader election is configured
    When I request the readiness endpoint
    Then the response should not include "split_brain_detected"
