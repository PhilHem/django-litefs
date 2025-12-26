Feature: Settings Domain Validation
  As a developer configuring LiteFS
  I need clear error messages when my configuration is invalid
  So that I can fix issues quickly without guessing

  The LiteFSSettings domain entity validates configuration values to ensure
  they are safe and consistent. This is framework-agnostic validation.

  # ---------------------------------------------------------------------------
  # Path Validation
  # ---------------------------------------------------------------------------

  Scenario: Paths must be absolute
    Given LiteFS settings with mount_path "litefs"
    Then a LiteFSConfigError should be raised
    And the error message should contain "absolute"

  Scenario: Path traversal attacks are rejected in mount_path
    Given LiteFS settings with mount_path "../../../etc/passwd"
    Then a LiteFSConfigError should be raised
    And the error message should contain "path traversal"

  Scenario: Path traversal attacks are rejected in data_path
    Given LiteFS settings with data_path "../../etc/passwd"
    Then a LiteFSConfigError should be raised
    And the error message should contain "path traversal"

  # ---------------------------------------------------------------------------
  # Database Name Validation
  # ---------------------------------------------------------------------------

  Scenario: Database name cannot be empty
    Given LiteFS settings with empty database_name
    Then a LiteFSConfigError should be raised
    And the error message should contain "database_name cannot be empty"

  Scenario: Database name cannot be whitespace only
    Given LiteFS settings with database_name "   "
    Then a LiteFSConfigError should be raised
    And the error message should contain "database_name cannot be empty"

  # ---------------------------------------------------------------------------
  # Leader Election Mode Validation
  # ---------------------------------------------------------------------------

  Scenario: Leader election must be 'static' or 'raft'
    Given LiteFS settings with leader_election "invalid"
    Then a LiteFSConfigError should be raised
    And the error message should contain "leader_election"

  Scenario: Static leader election is valid
    Given LiteFS settings with leader_election "static"
    Then the settings should be valid

  Scenario: Raft leader election is valid with proper config
    Given LiteFS settings with leader_election "raft"
    And raft_self_addr "node1:20202"
    And raft_peers "node2:20202,node3:20202"
    Then the settings should be valid

  # ---------------------------------------------------------------------------
  # Raft Mode Validation
  # ---------------------------------------------------------------------------

  Scenario: Raft mode requires raft_self_addr
    Given LiteFS settings with leader_election "raft"
    And raft_self_addr is not set
    And raft_peers "node2:20202"
    Then a LiteFSConfigError should be raised
    And the error message should contain "raft_self_addr"

  Scenario: Raft mode requires non-empty raft_self_addr
    Given LiteFS settings with leader_election "raft"
    And raft_self_addr is empty
    And raft_peers "node2:20202"
    Then a LiteFSConfigError should be raised
    And the error message should contain "raft_self_addr"

  Scenario: Raft mode requires raft_peers
    Given LiteFS settings with leader_election "raft"
    And raft_self_addr "node1:20202"
    And raft_peers is not set
    Then a LiteFSConfigError should be raised
    And the error message should contain "raft_peers"

  Scenario: Raft mode rejects empty peers list
    Given LiteFS settings with leader_election "raft"
    And raft_self_addr "node1:20202"
    And raft_peers is empty list
    Then a LiteFSConfigError should be raised
    And the error message should contain "raft_peers"

  # ---------------------------------------------------------------------------
  # Static Mode Ignores Raft Fields
  # ---------------------------------------------------------------------------

  Scenario: Static mode ignores raft fields even if invalid
    Given LiteFS settings with leader_election "static"
    And raft_self_addr is empty
    And raft_peers is empty list
    Then the settings should be valid
