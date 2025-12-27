# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: Write Request Forwarding - Resilience
  As a Django application developer
  I want forwarding to handle transient failures gracefully
  So that my application remains available during brief primary unavailability

  The WriteForwardingMiddleware implements resilience patterns:
  - Retry with exponential backoff for transient failures
  - Circuit breaker to fail fast when primary is down

  These patterns prevent cascade failures and improve user experience
  during infrastructure issues.

  See also: forwarding_core.feature, forwarding_config.feature

  TRA Namespace: Adapter.Http.WriteForwardingMiddleware.Resilience

  Background:
    Given the WriteForwardingMiddleware is enabled
    And this node is a replica

  # ---------------------------------------------------------------------------
  # Retry on Transient Failures
  # ---------------------------------------------------------------------------

  Scenario: Retry succeeds after transient connection failure
    Given retry count is configured as 3
    And the first 2 connection attempts fail
    And the 3rd attempt succeeds
    When a POST request arrives for "/api/resource"
    Then the request should succeed
    And 3 attempts should have been made

  Scenario Outline: Retry on gateway errors
    Given retry count is configured as 3
    And the first attempt returns <status>
    And the 2nd attempt succeeds
    When a POST request arrives for "/api/resource"
    Then the request should succeed after 2 attempts

    Examples:
      | status                  |
      | 502 Bad Gateway         |
      | 503 Service Unavailable |
      | 504 Gateway Timeout     |

  Scenario: No retry on client errors
    Given retry count is configured as 3
    And the primary returns 400 Bad Request
    When a POST request arrives for "/api/resource"
    Then the response status should be 400
    And only 1 attempt should have been made

  Scenario: No retry on server errors (non-gateway)
    Given retry count is configured as 3
    And the primary returns 500 Internal Server Error
    When a POST request arrives for "/api/resource"
    Then the response status should be 500
    And only 1 attempt should have been made

  Scenario: Exponential backoff between retries
    Given retry count is configured as 3
    And retry backoff base is 0.5 seconds
    And all connection attempts fail
    When a POST request arrives for "/api/resource"
    Then the delays between attempts should increase exponentially
    And the response status should be 502

  Scenario: All retries exhausted returns error
    Given retry count is configured as 3
    And all connection attempts fail
    When a POST request arrives for "/api/resource"
    Then the response status should be 502 Bad Gateway
    And 3 attempts should have been made

  Scenario: Retry disabled when count is zero
    Given retry count is configured as 0
    And the connection attempt fails
    When a POST request arrives for "/api/resource"
    Then the response status should be 502
    And only 1 attempt should have been made

  # ---------------------------------------------------------------------------
  # Circuit Breaker
  # ---------------------------------------------------------------------------

  Scenario: Circuit opens after failure threshold
    Given circuit breaker threshold is 5 failures
    And the primary has failed 5 consecutive requests
    When a POST request arrives for "/api/resource"
    Then the circuit breaker should be open
    And the response status should be 503 Service Unavailable
    And no forwarding attempt should be made
    And the response should include "Retry-After" header

  Scenario: Open circuit rejects requests immediately
    Given the circuit breaker is open
    When a POST request arrives for "/api/resource"
    Then the response status should be 503
    And no forwarding attempt should be made

  Scenario: Circuit allows probe after reset timeout
    Given the circuit breaker is open
    And the reset timeout has elapsed
    When a POST request arrives for "/api/resource"
    Then a probe request should be made to the primary
    And the circuit should be half-open

  Scenario: Successful probe closes circuit
    Given the circuit breaker is half-open
    And the primary responds successfully
    When a POST request arrives for "/api/resource"
    Then the circuit breaker should close
    And subsequent requests should be forwarded normally

  Scenario: Failed probe reopens circuit
    Given the circuit breaker is half-open
    And the primary is still unavailable
    When a POST request arrives for "/api/resource"
    Then the circuit breaker should reopen
    And the reset timeout should restart

  Scenario: Circuit breaker can be disabled
    Given circuit breaker is disabled
    And the primary has failed 10 consecutive requests
    When a POST request arrives for "/api/resource"
    Then a forwarding attempt should be made
    And the response status should be 502
