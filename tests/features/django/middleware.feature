# @bdd-decomposed: 2025-12-26 epic=django-litefs-h9m status=complete
Feature: LiteFS Django Middleware
  As a Django application developer
  I want middleware that handles LiteFS cluster concerns transparently
  So that my application remains available and consistent without manual intervention

  The LiteFS middleware stack provides two key capabilities:
  1. Split-brain protection - Blocks all requests during split-brain to prevent data corruption
  2. Write request forwarding - Routes write requests to the primary node transparently

  These middleware components work together to provide seamless multi-node operation
  while protecting data integrity during cluster failures.

  # ---------------------------------------------------------------------------
  # Split-Brain Protection - Request Blocking
  # ---------------------------------------------------------------------------

  Scenario: Requests blocked during split-brain condition
    Given the cluster is in a split-brain state with 2 leaders
    When any HTTP request arrives
    Then the response status should be 503 Service Unavailable
    And the response should include header "Retry-After: 30"

  Scenario: Requests allowed when cluster is healthy
    Given the cluster has exactly one leader
    When any HTTP request arrives
    Then the request should proceed to the next middleware

  Scenario: Requests allowed when cluster is leaderless
    Given the cluster has zero leaders
    When any HTTP request arrives
    Then the request should proceed to the next middleware
    And a warning should be logged about leaderless state

  # ---------------------------------------------------------------------------
  # Split-Brain Protection - Fail-Open Behavior
  # ---------------------------------------------------------------------------

  Scenario: Middleware fails open when detection errors occur
    Given split-brain detection is unavailable
    When any HTTP request arrives
    Then the request should proceed to the next middleware
    And an error should be logged about detection failure

  Scenario: Middleware fails open when cluster state is unknown
    Given the cluster state cannot be determined
    When any HTTP request arrives
    Then the request should proceed to the next middleware

  # ---------------------------------------------------------------------------
  # Split-Brain Protection - Signal Integration
  # ---------------------------------------------------------------------------

  Scenario: Signal emitted when split-brain detected
    Given the cluster is in a split-brain state with 3 leaders
    When any HTTP request arrives
    Then the split_brain_detected signal should be sent
    And the signal should include the leader node IDs
    And the signal should include the leader count

  Scenario: No signal emitted for healthy cluster
    Given the cluster has exactly one leader
    When any HTTP request arrives
    Then the split_brain_detected signal should not be sent

  # ---------------------------------------------------------------------------
  # Split-Brain Protection - Leader Election Mode
  # ---------------------------------------------------------------------------

  Scenario: Split-brain check skipped for static leader election
    Given LiteFS is configured with static leader election
    When any HTTP request arrives
    Then split-brain detection should not be performed
    And the request should proceed to the next middleware

  Scenario: Split-brain check performed for Raft leader election
    Given LiteFS is configured with Raft leader election
    And the cluster has exactly one leader
    When any HTTP request arrives
    Then split-brain detection should be performed
    And the request should proceed to the next middleware

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Detection
  # ---------------------------------------------------------------------------

  Scenario: POST request detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a POST request arrives
    Then the request should be identified as a write request

  Scenario: PUT request detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a PUT request arrives
    Then the request should be identified as a write request

  Scenario: PATCH request detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a PATCH request arrives
    Then the request should be identified as a write request

  Scenario: DELETE request detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a DELETE request arrives
    Then the request should be identified as a write request

  Scenario: GET request not detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a GET request arrives
    Then the request should be identified as a read request
    And the request should proceed locally

  Scenario: HEAD request not detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When a HEAD request arrives
    Then the request should be identified as a read request

  Scenario: OPTIONS request not detected as write request
    Given the current node is a replica
    And write forwarding is enabled
    When an OPTIONS request arrives
    Then the request should be identified as a read request

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Primary Node Behavior
  # ---------------------------------------------------------------------------

  Scenario: Write request proceeds locally on primary node
    Given the current node is the primary
    And write forwarding is enabled
    When a POST request arrives
    Then the request should proceed locally
    And no forwarding should occur

  Scenario: Read request proceeds locally on primary node
    Given the current node is the primary
    And write forwarding is enabled
    When a GET request arrives
    Then the request should proceed locally

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Replica Node Behavior
  # ---------------------------------------------------------------------------

  Scenario: Write request forwarded from replica to primary
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable at "http://primary:8000"
    When a POST request arrives with path "/api/users/"
    Then the request should be forwarded to "http://primary:8000/api/users/"
    And the forwarded response should be returned to the client

  Scenario: Forwarded request preserves request body
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives with body '{"name": "test"}'
    Then the forwarded request should include body '{"name": "test"}'

  Scenario: Forwarded request preserves headers
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives with header "Authorization: Bearer token123"
    Then the forwarded request should include header "Authorization: Bearer token123"

  Scenario: Forwarded request includes forwarding headers
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives
    Then the forwarded request should include header "X-Forwarded-For"
    And the forwarded request should include header "X-Forwarded-Host"

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Error Handling
  # ---------------------------------------------------------------------------

  Scenario: Forwarding fails when primary unreachable
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is unreachable
    When a POST request arrives
    Then the response status should be 503 Service Unavailable
    And the response should indicate primary unavailable

  Scenario: Forwarding fails with timeout
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node times out
    When a POST request arrives
    Then the response status should be 504 Gateway Timeout

  Scenario: Forwarding retries on transient failure
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node fails once then succeeds
    When a POST request arrives
    Then the request should be retried
    And the successful response should be returned

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Configuration
  # ---------------------------------------------------------------------------

  Scenario: Write forwarding disabled by default
    Given write forwarding is not configured
    And the current node is a replica
    When a POST request arrives
    Then no forwarding should occur
    And the request should proceed locally

  Scenario: Write forwarding can be explicitly disabled
    Given write forwarding is explicitly disabled
    And the current node is a replica
    When a POST request arrives
    Then no forwarding should occur

  Scenario: Forwarding timeout is configurable
    Given write forwarding is enabled with timeout 5 seconds
    And the current node is a replica
    And the primary node takes 3 seconds to respond
    When a POST request arrives
    Then the forwarded response should be returned

  Scenario: Forwarding timeout exceeded
    Given write forwarding is enabled with timeout 2 seconds
    And the current node is a replica
    And the primary node takes 5 seconds to respond
    When a POST request arrives
    Then the response status should be 504 Gateway Timeout

  # ---------------------------------------------------------------------------
  # Write Request Forwarding - Path Exclusions
  # ---------------------------------------------------------------------------

  Scenario: Health check paths excluded from forwarding
    Given the current node is a replica
    And write forwarding is enabled
    And path "/health/" is excluded from forwarding
    When a POST request arrives with path "/health/"
    Then no forwarding should occur
    And the request should proceed locally

  Scenario: Admin paths can be excluded from forwarding
    Given the current node is a replica
    And write forwarding is enabled
    And path pattern "/admin/*" is excluded from forwarding
    When a POST request arrives with path "/admin/login/"
    Then no forwarding should occur

  Scenario: API paths are forwarded by default
    Given the current node is a replica
    And write forwarding is enabled
    And path "/health/" is excluded from forwarding
    When a POST request arrives with path "/api/users/"
    Then the request should be forwarded to primary

  # ---------------------------------------------------------------------------
  # Middleware Configuration - LiteFS Disabled
  # ---------------------------------------------------------------------------

  Scenario: Middleware inactive when LiteFS disabled
    Given LiteFS is disabled in settings
    When any HTTP request arrives
    Then split-brain detection should not be performed
    And no forwarding should occur
    And the request should proceed to the next middleware

  Scenario: Middleware inactive when settings missing
    Given LiteFS settings are not configured
    When any HTTP request arrives
    Then the request should proceed to the next middleware
    And a debug message should be logged

  # ---------------------------------------------------------------------------
  # Middleware Order - Split-Brain Before Forwarding
  # ---------------------------------------------------------------------------

  Scenario: Split-brain blocks before forwarding is attempted
    Given the cluster is in a split-brain state
    And write forwarding is enabled
    And the current node is a replica
    When a POST request arrives
    Then the response status should be 503 Service Unavailable
    And no forwarding should be attempted

  Scenario: Forwarding proceeds after split-brain check passes
    Given the cluster has exactly one leader
    And write forwarding is enabled
    And the current node is a replica
    When a POST request arrives
    Then split-brain detection should be performed first
    And then forwarding should be attempted

  # ---------------------------------------------------------------------------
  # Idempotency and Safety
  # ---------------------------------------------------------------------------

  Scenario: Non-idempotent requests include idempotency key
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives without an idempotency key
    Then the forwarded request should include header "X-Idempotency-Key"

  Scenario: Existing idempotency key preserved
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives with header "X-Idempotency-Key: abc123"
    Then the forwarded request should include header "X-Idempotency-Key: abc123"

  # ---------------------------------------------------------------------------
  # Observability
  # ---------------------------------------------------------------------------

  Scenario: Forwarded requests are logged
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is reachable
    When a POST request arrives
    Then a log entry should indicate the request was forwarded
    And the log should include the target primary URL

  Scenario: Forwarding failures are logged with details
    Given the current node is a replica
    And write forwarding is enabled
    And the primary node is unreachable
    When a POST request arrives
    Then an error log should include the failure reason
    And the error log should include the attempted primary URL
