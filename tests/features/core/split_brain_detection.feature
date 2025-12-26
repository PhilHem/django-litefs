# @bdd-decomposed: 2025-12-26 status=implemented
Feature: Split-Brain Detection
  As a distributed application
  I want to detect when multiple nodes claim leadership
  So that conflicting writes can be prevented and data consistency maintained

  A split-brain occurs when network partitions cause cluster consensus to break
  down, resulting in multiple nodes believing they are the leader simultaneously.
  This is a critical failure mode that must be detected before accepting writes.

  Detection rule: 2+ nodes claiming leadership = split-brain condition.
  - 0 leaders: Not split-brain (leaderless, but not conflicting)
  - 1 leader: Healthy cluster
  - 2+ leaders: Split-brain detected

  # ---------------------------------------------------------------------------
  # RaftNodeState Value Object - Validation
  # ---------------------------------------------------------------------------

  Scenario: RaftNodeState requires non-empty node_id
    When I create a RaftNodeState with empty node_id
    Then a LiteFSConfigError should be raised
    And the error message should contain "node_id cannot be empty"

  Scenario: RaftNodeState rejects whitespace-only node_id
    When I create a RaftNodeState with whitespace-only node_id
    Then a LiteFSConfigError should be raised
    And the error message should contain "node_id cannot be whitespace"

  Scenario: RaftNodeState accepts valid node_id
    When I create a RaftNodeState with node_id "node1" and is_leader true
    Then the RaftNodeState should be valid
    And the node_id should be "node1"
    And is_leader should be true

  # ---------------------------------------------------------------------------
  # RaftClusterState Value Object - Validation
  # ---------------------------------------------------------------------------

  Scenario: RaftClusterState requires non-empty nodes list
    When I create a RaftClusterState with empty nodes list
    Then a LiteFSConfigError should be raised
    And the error message should contain "nodes list cannot be empty"

  Scenario: RaftClusterState accepts valid nodes list
    Given a cluster with nodes:
      | node_id | is_leader |
      | node1   | true      |
      | node2   | false     |
      | node3   | false     |
    Then the RaftClusterState should be valid
    And count_leaders should return 1

  # ---------------------------------------------------------------------------
  # RaftClusterState - Leader Counting
  # ---------------------------------------------------------------------------

  Scenario: Cluster with single leader reports one leader
    Given a cluster with nodes:
      | node_id | is_leader |
      | node1   | true      |
      | node2   | false     |
      | node3   | false     |
    Then count_leaders should return 1
    And has_single_leader should be true

  Scenario: Cluster with no leaders reports zero leaders
    Given a cluster with nodes:
      | node_id | is_leader |
      | node1   | false     |
      | node2   | false     |
      | node3   | false     |
    Then count_leaders should return 0
    And has_single_leader should be false

  Scenario: Cluster with multiple leaders reports all leaders
    Given a cluster with nodes:
      | node_id | is_leader |
      | node1   | true      |
      | node2   | true      |
      | node3   | false     |
    Then count_leaders should return 2
    And has_single_leader should be false
    And get_leader_nodes should return nodes "node1" and "node2"

  # ---------------------------------------------------------------------------
  # SplitBrainDetector Use Case - Detection Logic
  # ---------------------------------------------------------------------------

  Scenario: No split-brain when exactly one leader exists
    Given a cluster with single leader "node1"
    When I check for split-brain
    Then is_split_brain should be false
    And leader_nodes should contain 1 node

  Scenario: No split-brain when zero leaders exist
    Given a cluster with no leaders
    When I check for split-brain
    Then is_split_brain should be false
    And leader_nodes should be empty

  Scenario: Split-brain detected when two nodes claim leadership
    Given a cluster where "node1" and "node2" both claim leadership
    When I check for split-brain
    Then is_split_brain should be true
    And leader_nodes should contain 2 nodes

  Scenario: Split-brain detected when all nodes claim leadership
    Given a cluster where all 3 nodes claim leadership
    When I check for split-brain
    Then is_split_brain should be true
    And leader_nodes should contain 3 nodes

  # ---------------------------------------------------------------------------
  # SplitBrainStatus Value Object - Immutability
  # ---------------------------------------------------------------------------

  Scenario: SplitBrainStatus is immutable
    Given a SplitBrainStatus with is_split_brain true
    When I attempt to modify is_split_brain
    Then a FrozenInstanceError should be raised
