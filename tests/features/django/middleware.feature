# @bdd-decomposed: 2025-12-26 epic=django-litefs-h9m status=complete
Feature: LiteFS Django Middleware - Split-Brain Protection
  As a Django application developer
  I want middleware that protects my application during split-brain conditions
  So that data corruption is prevented when cluster consensus fails

  The SplitBrainMiddleware blocks all requests during split-brain conditions
  (multiple nodes claiming leadership) to prevent conflicting writes.

  This middleware provides:
  - Request blocking when 2+ leaders detected
  - Fail-open behavior on detection errors
  - Django signals for split-brain events
  - Static leader election mode support

  TRA Namespace: Adapter.Http.SplitBrainMiddleware

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
  # Middleware Configuration - LiteFS Disabled
  # ---------------------------------------------------------------------------

  Scenario: Middleware inactive when LiteFS disabled
    Given LiteFS is disabled in settings
    When any HTTP request arrives
    Then split-brain detection should not be performed
    And the request should proceed to the next middleware

  Scenario: Middleware inactive when settings missing
    Given LiteFS settings are not configured
    When any HTTP request arrives
    Then the request should proceed to the next middleware
    And a debug message should be logged

# -----------------------------------------------------------------------------
# ROADMAP: Write Request Forwarding
# -----------------------------------------------------------------------------
# The following scenarios describe PLANNED functionality for write request
# forwarding. This feature is NOT YET IMPLEMENTED.
#
# When implemented, move these to a separate feature file and create beads tasks.
#
# Planned capabilities:
# - Forward POST/PUT/PATCH/DELETE requests from replica to primary
# - Preserve request headers and body
# - Configurable timeouts and path exclusions
# - Retry on transient failures
#
# Related beads issues (currently blocked):
# - django-litefs-h9m.1: Create ForwardingSettings domain value object
# - django-litefs-h9m.2: Create HttpForwardingPort interface
# - django-litefs-h9m.3: Create WriteForwardingMiddleware
# - django-litefs-h9m.4: Create FakeHttpForwardingAdapter for testing
# - django-litefs-h9m.5: Create HttpxForwardingAdapter
# -----------------------------------------------------------------------------
