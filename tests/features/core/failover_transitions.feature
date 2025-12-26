# @bdd-decomposed: 2025-12-26 epic=django-litefs-c7h status=complete
Feature: Failover State Transitions
  As a distributed application
  I want automatic failover when the primary node fails
  So that the cluster remains available for writes without operator intervention

  The FailoverCoordinator orchestrates state transitions between PRIMARY and REPLICA
  states based on leader election, node health, and cluster quorum. Transitions are
  idempotent and guarded by health and quorum checks to prevent split-brain scenarios.

  Background:
    Given a 3-node LiteFS cluster with Raft consensus

  # Happy Path: Replica Promotion
  Scenario: Replica is promoted when elected and healthy
    Given a replica node
    And the node is marked healthy
    And quorum is reached
    When leader election completes with this node as leader
    Then the node state transitions to PRIMARY
    And the node can accept write operations

  Scenario: Primary maintains leadership when conditions are met
    Given a primary node
    And the node is marked healthy
    And quorum is reached
    And leader election confirms this node as leader
    When failover coordination runs
    Then the node state remains PRIMARY

  # Graceful Handoff
  Scenario: Primary performs graceful handoff on demotion request
    Given a primary node
    When graceful handoff is requested
    Then pending writes are completed
    And leadership is released to the cluster
    And the node state transitions to REPLICA

  # Health-Aware Failover
  Scenario: Unhealthy replica cannot be promoted
    Given a replica node
    And the node is marked unhealthy
    And leader election completes with this node as leader
    When failover coordination runs
    Then the node state remains REPLICA
    And a warning is logged about health blocking promotion

  Scenario: Primary demotes when marked unhealthy
    Given a primary node
    When the node is marked unhealthy
    And failover coordination runs
    Then the node state transitions to REPLICA
    And a health-triggered demotion event is emitted

  # Quorum-Aware Failover
  Scenario: Replica cannot be promoted without quorum
    Given a replica node
    And the node is marked healthy
    And quorum is NOT reached due to network partition
    And leader election completes with this node as leader
    When failover coordination runs
    Then the node state remains REPLICA
    And a warning is logged about quorum blocking promotion

  Scenario: Primary demotes when quorum is lost
    Given a primary node
    And the node is marked healthy
    And quorum was previously reached
    When quorum is lost due to network partition
    And failover coordination runs
    Then the node state transitions to REPLICA
    And a quorum-loss demotion event is emitted

  # Idempotence
  Scenario: Repeated promotion attempts are idempotent
    Given a primary node
    When failover coordination runs multiple times
    Then the node state remains PRIMARY
    And no redundant state change events are emitted
