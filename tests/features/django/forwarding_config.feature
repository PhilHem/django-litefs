# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: Write Request Forwarding - Configuration
  As a Django application developer
  I want to configure forwarding behavior for my deployment
  So that I can tune timeouts, exclude paths, and control middleware behavior

  The WriteForwardingMiddleware is configurable via Django settings:
  - Timeouts (connect, read)
  - Path exclusions (exact, wildcard, regex)
  - Primary discovery (auto from LiteFS, manual override)
  - Enable/disable toggle

  See also: forwarding_core.feature, forwarding_resilience.feature

  TRA Namespace: Adapter.Http.WriteForwardingMiddleware.Config

  # ---------------------------------------------------------------------------
  # Timeout Configuration
  # ---------------------------------------------------------------------------

  Scenario: Default timeout is 30 seconds
    Given no explicit forwarding timeout is configured
    And this node is a replica
    When a POST request is forwarded
    Then the forwarding timeout should be 30 seconds

  Scenario: Custom timeout applied
    Given forwarding timeout is configured as 60 seconds
    And this node is a replica
    When a POST request is forwarded
    Then the forwarding timeout should be 60 seconds

  Scenario: Request fails when forwarding times out
    Given forwarding timeout is configured as 5 seconds
    And the primary takes 10 seconds to respond
    And this node is a replica
    When a POST request arrives for "/api/resource"
    Then the response status should be 504 Gateway Timeout
    And the response should include "X-LiteFS-Forwarding-Error: timeout"

  Scenario: Separate connect and read timeouts
    Given forwarding connect timeout is 5 seconds
    And forwarding read timeout is 30 seconds
    And this node is a replica
    When a POST request is forwarded
    Then the connect timeout should be 5 seconds
    And the read timeout should be 30 seconds

  # ---------------------------------------------------------------------------
  # Path Exclusions
  # ---------------------------------------------------------------------------

  Scenario: Excluded exact path not forwarded
    Given path "/health" is excluded from forwarding
    And this node is a replica
    When a POST request arrives for "/health"
    Then the request should proceed to the next middleware
    And no forwarding should occur

  Scenario: Multiple path exclusions
    Given paths are excluded from forwarding:
      | path         |
      | /health      |
      | /metrics     |
      | /admin/login |
    And this node is a replica
    When a POST request arrives for "/metrics"
    Then no forwarding should occur

  Scenario: Wildcard path exclusion
    Given path pattern "/internal/*" is excluded from forwarding
    And this node is a replica
    When a POST request arrives for "/internal/status"
    Then no forwarding should occur

  Scenario: Regex path exclusion
    Given path regex "^/api/v[0-9]+/health$" is excluded from forwarding
    And this node is a replica
    When a POST request arrives for "/api/v2/health"
    Then no forwarding should occur

  Scenario: Non-excluded path still forwarded
    Given path "/health" is excluded from forwarding
    And this node is a replica
    And the primary node is reachable
    When a POST request arrives for "/api/resource"
    Then the request should be forwarded to the primary

  # ---------------------------------------------------------------------------
  # Primary Discovery
  # ---------------------------------------------------------------------------

  Scenario: Primary discovered from LiteFS mount
    Given this node is a replica
    And LiteFS mount indicates primary is "primary.local:8000"
    When a POST request is forwarded
    Then the request should be sent to "http://primary.local:8000"

  Scenario: Primary URL uses configured scheme
    Given forwarding scheme is configured as "https"
    And LiteFS mount indicates primary is "primary.local:8000"
    And this node is a replica
    When a POST request is forwarded
    Then the request should be sent to "https://primary.local:8000"

  Scenario: Forwarding fails when primary unknown
    Given this node is a replica
    And the primary node is unknown
    When a POST request arrives for "/api/resource"
    Then the response status should be 503 Service Unavailable
    And the response body should indicate "primary node unknown"

  # ---------------------------------------------------------------------------
  # Middleware Ordering
  # ---------------------------------------------------------------------------

  Scenario: Split-brain middleware runs before forwarding
    Given SplitBrainMiddleware is before WriteForwardingMiddleware
    And a split-brain condition exists
    When a POST request arrives for "/api/resource"
    Then the response status should be 503
    And the response should be from SplitBrainMiddleware
    And no forwarding should occur

  # ---------------------------------------------------------------------------
  # Enable/Disable States
  # ---------------------------------------------------------------------------

  Scenario: Forwarding disabled when LiteFS disabled
    Given LiteFS is disabled in settings
    When a POST request arrives for "/api/resource"
    Then the request should proceed to the next middleware
    And no forwarding should occur

  Scenario: Forwarding disabled by explicit configuration
    Given write forwarding is explicitly disabled
    And this node is a replica
    When a POST request arrives for "/api/resource"
    Then the request should proceed to the next middleware
    And no forwarding should occur

  Scenario: Forwarding inactive when settings missing
    Given LiteFS settings are not configured
    When a POST request arrives for "/api/resource"
    Then the request should proceed to the next middleware

  # ---------------------------------------------------------------------------
  # Settings Structure
  # ---------------------------------------------------------------------------

  Scenario: Forwarding settings in LITEFS dict
    Given Django settings contain:
      """
      LITEFS = {
          'mount_path': '/mnt/litefs',
          'forwarding': {
              'enabled': True,
              'timeout': 60,
              'retry_count': 3,
              'excluded_paths': ['/health', '/metrics'],
          }
      }
      """
    When the middleware initializes
    Then forwarding should be enabled with timeout 60 seconds
    And retry count should be 3
    And "/health" and "/metrics" should be excluded
