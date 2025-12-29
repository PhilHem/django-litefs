# @bdd-decomposed: 2025-12-26 status=implemented
Feature: Primary Initializer - Static Leader Detection
  In static leader election mode, one node is pre-designated as primary.
  The PrimaryInitializer compares hostnames to determine primary status.

  The PrimaryInitializer use case performs a simple comparison between the
  current node's hostname and the configured primary hostname. This is a
  stateless, case-sensitive exact string match with no normalization.

  In static leader election mode, one node is pre-designated as primary.
  All other nodes become replicas that forward writes to the primary.

  # ---------------------------------------------------------------------------
  # Happy Path - Exact Match
  # ---------------------------------------------------------------------------

  Scenario: Node is primary when hostname matches exactly
    Given a static leader config with primary_hostname "node1"
    And the current node hostname is "node1"
    When I check if the node is primary
    Then the result should be true

  Scenario: Node is replica when hostname does not match
    Given a static leader config with primary_hostname "node1"
    And the current node hostname is "node2"
    When I check if the node is primary
    Then the result should be false

  # ---------------------------------------------------------------------------
  # Case Sensitivity
  # ---------------------------------------------------------------------------

  Scenario: Comparison is case-sensitive - uppercase vs lowercase
    Given a static leader config with primary_hostname "Node1"
    And the current node hostname is "node1"
    When I check if the node is primary
    Then the result should be false

  Scenario: Comparison is case-sensitive - lowercase vs uppercase
    Given a static leader config with primary_hostname "node1"
    And the current node hostname is "NODE1"
    When I check if the node is primary
    Then the result should be false

  # ---------------------------------------------------------------------------
  # No Partial Matching
  # ---------------------------------------------------------------------------

  Scenario: No prefix matching
    Given a static leader config with primary_hostname "web-server"
    And the current node hostname is "web-server-01"
    When I check if the node is primary
    Then the result should be false

  Scenario: No suffix matching
    Given a static leader config with primary_hostname "server-01"
    And the current node hostname is "web-server-01"
    When I check if the node is primary
    Then the result should be false

  # ---------------------------------------------------------------------------
  # Hostname Formats
  # ---------------------------------------------------------------------------

  Scenario: FQDN hostnames are supported
    Given a static leader config with primary_hostname "node1.example.com"
    And the current node hostname is "node1.example.com"
    When I check if the node is primary
    Then the result should be true

  Scenario: IP addresses are supported
    Given a static leader config with primary_hostname "192.168.1.100"
    And the current node hostname is "192.168.1.100"
    When I check if the node is primary
    Then the result should be true

  Scenario: Hyphenated hostnames are supported
    Given a static leader config with primary_hostname "web-app-primary-01"
    And the current node hostname is "web-app-primary-01"
    When I check if the node is primary
    Then the result should be true

  # ---------------------------------------------------------------------------
  # Statelessness
  # ---------------------------------------------------------------------------

  Scenario: Multiple checks are independent
    Given a static leader config with primary_hostname "node1"
    When I check is_primary with "node1"
    Then the result should be true
    When I check is_primary with "node2"
    Then the result should be false
    When I check is_primary with "node1"
    Then the result should be true
