# @bdd-decomposed: 2025-12-27 status=decomposed
Feature: Write Request Forwarding - Core Behavior
  As a Django application developer
  I want write requests automatically forwarded from replicas to the primary
  So that my application works transparently regardless of which node receives the request

  The WriteForwardingMiddleware transparently forwards write requests (POST, PUT,
  PATCH, DELETE) from replica nodes to the primary node. This enables horizontal
  scaling where any node can receive any request, with writes automatically routed
  to the primary.

  NOTE: This is HTTP-level forwarding, complementing (not replacing) LiteFS's
  built-in proxy forwarding. Use cases:
  - When not using LiteFS proxy mode
  - When application logic needs request context during forwarding
  - When custom headers or transformations are required

  See also: forwarding_resilience.feature, forwarding_config.feature

  TRA Namespace: Adapter.Http.WriteForwardingMiddleware

  Background:
    Given the WriteForwardingMiddleware is enabled

  # ---------------------------------------------------------------------------
  # HTTP Method Routing
  # ---------------------------------------------------------------------------

  Scenario Outline: Write methods forwarded from replica to primary
    Given this node is a replica
    And the primary node is reachable
    When a <method> request arrives for "/api/resource"
    Then the request should be forwarded to the primary
    And the forwarded request method should be "<method>"

    Examples:
      | method |
      | POST   |
      | PUT    |
      | PATCH  |
      | DELETE |

  Scenario Outline: Read methods handled locally on replica
    Given this node is a replica
    When a <method> request arrives for "/api/resource"
    Then the request should proceed to the next middleware
    And no forwarding should occur

    Examples:
      | method  |
      | GET     |
      | HEAD    |
      | OPTIONS |

  Scenario: Write request handled locally on primary
    Given this node is the primary
    When a POST request arrives for "/api/resource"
    Then the request should proceed to the next middleware
    And no forwarding should occur

  # ---------------------------------------------------------------------------
  # Request Header Preservation
  # ---------------------------------------------------------------------------

  Scenario: Authorization and custom headers preserved
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives with headers:
      | header          | value            |
      | Authorization   | Bearer token123  |
      | Content-Type    | application/json |
      | X-Custom-Header | custom-value     |
    Then the forwarded request should include all original headers

  Scenario: Host header rewritten to primary
    Given this node is a replica
    And the primary node is at "primary.local:8000"
    When a POST request arrives with Host header "replica.local:8000"
    Then the forwarded request Host header should be "primary.local:8000"

  Scenario: X-Forwarded-For header added
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives from client IP "192.168.1.100"
    Then the forwarded request should include "X-Forwarded-For: 192.168.1.100"
    And the forwarded request should include "X-Forwarded-Host" with original host
    And the forwarded request should include "X-Forwarded-Proto" with original protocol

  Scenario: Existing X-Forwarded-For header appended
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives with "X-Forwarded-For: 10.0.0.1"
    And the client IP is "192.168.1.100"
    Then the forwarded "X-Forwarded-For" should be "10.0.0.1, 192.168.1.100"

  # ---------------------------------------------------------------------------
  # Request Body Preservation
  # ---------------------------------------------------------------------------

  Scenario: JSON body preserved during forwarding
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives with JSON body:
      """
      {"name": "test", "value": 123}
      """
    Then the forwarded request body should be identical

  Scenario: Form data preserved during forwarding
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives with form data:
      | field    | value    |
      | username | testuser |
      | password | secret   |
    Then the forwarded request should preserve the form data

  Scenario: Query parameters preserved during forwarding
    Given this node is a replica
    And the primary node is reachable
    When a POST request arrives for "/api/resource?page=1&filter=active"
    Then the forwarded request path should include the query string

  # ---------------------------------------------------------------------------
  # Response Passthrough
  # ---------------------------------------------------------------------------

  Scenario: Success response passed through
    Given this node is a replica
    And the primary returns status 201 with body '{"id": 123}'
    When a POST request arrives for "/api/resource"
    Then the response status should be 201
    And the response body should be '{"id": 123}'

  Scenario: Response headers passed through
    Given this node is a replica
    And the primary returns headers:
      | header          | value          |
      | X-Custom-Header | custom-value   |
      | Set-Cookie      | session=abc123 |
    When a POST request arrives for "/api/resource"
    Then the response should include all primary response headers

  Scenario: Error response passed through
    Given this node is a replica
    And the primary returns status 422 with body '{"error": "validation failed"}'
    When a POST request arrives for "/api/resource"
    Then the response status should be 422
    And the response body should be '{"error": "validation failed"}'

  Scenario: Redirect response passed through
    Given this node is a replica
    And the primary returns status 302 with Location "/api/resource/123"
    When a POST request arrives for "/api/resource"
    Then the response status should be 302
    And the response should include "Location: /api/resource/123"

  # ---------------------------------------------------------------------------
  # Forwarding Indicator Headers
  # ---------------------------------------------------------------------------

  Scenario: Forwarded response includes indicator header
    Given this node is a replica
    And the primary node is reachable
    When a POST request is forwarded successfully
    Then the response should include "X-LiteFS-Forwarded: true"
    And the response should include "X-LiteFS-Primary-Node" with node ID

  Scenario: Local response excludes forwarding indicator
    Given this node is the primary
    When a POST request arrives for "/api/resource"
    Then the response should not include "X-LiteFS-Forwarded"
