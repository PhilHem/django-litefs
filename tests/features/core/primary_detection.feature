# @bdd-decomposed: 2025-12-26 status=implemented
Feature: Primary Node Detection
  As a LiteFS node
  I need to know if I am the primary node
  So that write operations can be routed correctly

  LiteFS uses a `.primary` file in the mount path to indicate which node
  holds the write lease. This file is managed by LiteFS itself - when a node
  becomes primary, LiteFS creates the file; when it loses the lease, the file
  is removed.

  Background:
    Given a LiteFS mount path

  Scenario: Node is primary when .primary file exists
    Given the ".primary" file exists in the mount path
    When I check if the node is primary
    Then the result should be true

  Scenario: Node is replica when .primary file does not exist
    Given the ".primary" file does not exist in the mount path
    When I check if the node is primary
    Then the result should be false

  Scenario: Error when LiteFS mount path does not exist
    Given the mount path does not exist
    When I check if the node is primary
    Then a LiteFSNotRunningError should be raised
    And the error message should contain "does not exist"
