# @bdd-decomposed: 2025-12-26 status=implemented
Feature: LiteFS Configuration Generation
  As a LiteFS deployment operator
  I need to generate valid LiteFS YAML configuration from settings
  So that LiteFS can be started with the correct parameters

  The ConfigGenerator transforms LiteFSSettings domain entities into YAML
  configuration files that LiteFS can consume. The generated YAML includes
  sections for FUSE mount, data directory, databases, lease type, and proxy.

  # ---------------------------------------------------------------------------
  # Basic Configuration Generation
  # ---------------------------------------------------------------------------

  Scenario: Minimal configuration is generated correctly
    Given LiteFS settings with:
      | field           | value           |
      | mount_path      | /mnt/litefs     |
      | data_path       | /var/lib/litefs |
      | database_name   | db.sqlite3      |
      | leader_election | static          |
      | proxy_addr      | :8080           |
    When I generate the configuration
    Then the YAML should contain fuse.dir "/mnt/litefs"
    And the YAML should contain data.dir "/var/lib/litefs"
    And the YAML should contain databases[0].path "db.sqlite3"
    And the YAML should contain lease.type "static"
    And the YAML should contain proxy.addr ":8080"

  Scenario: Configuration with raft leader election
    Given LiteFS settings with:
      | field           | value           |
      | mount_path      | /mnt/litefs     |
      | data_path       | /var/lib/litefs |
      | database_name   | db.sqlite3      |
      | leader_election | raft            |
      | proxy_addr      | :8080           |
    When I generate the configuration
    Then the YAML should contain lease.type "raft"

  # ---------------------------------------------------------------------------
  # Proxy Configuration
  # ---------------------------------------------------------------------------

  Scenario: Configuration without detailed proxy settings
    Given LiteFS settings with proxy_addr ":8080" only
    When I generate the configuration
    Then the YAML should contain proxy.addr ":8080"
    And the YAML should NOT contain proxy.target
    And the YAML should NOT contain proxy.db

  Scenario: Configuration with detailed proxy settings
    Given LiteFS settings with proxy settings:
      | field                    | value          |
      | target                   | localhost:8081 |
      | db                       | db.sqlite3     |
      | passthrough              | /static/*      |
      | primary_redirect_timeout | 5s             |
    When I generate the configuration
    Then the YAML should contain proxy.target "localhost:8081"
    And the YAML should contain proxy.db "db.sqlite3"
    And the YAML should contain proxy.passthrough "/static/*"
    And the YAML should contain proxy.primary_redirect_timeout "5s"

  # ---------------------------------------------------------------------------
  # YAML Output Validity
  # ---------------------------------------------------------------------------

  Scenario: Generated configuration is valid YAML
    Given LiteFS settings with:
      | field           | value           |
      | mount_path      | /mnt/litefs     |
      | data_path       | /var/lib/litefs |
      | database_name   | db.sqlite3      |
      | leader_election | static          |
      | proxy_addr      | :8080           |
    When I generate the configuration
    Then the output should be valid YAML
    And the output should be parseable back to a dictionary

  Scenario: Generated configuration uses block style YAML
    Given LiteFS settings with:
      | field           | value           |
      | mount_path      | /mnt/litefs     |
      | data_path       | /var/lib/litefs |
      | database_name   | db.sqlite3      |
      | leader_election | static          |
      | proxy_addr      | :8080           |
    When I generate the configuration
    Then the output should NOT contain flow style braces

  # ---------------------------------------------------------------------------
  # Path Handling
  # ---------------------------------------------------------------------------

  Scenario: Paths with special characters are preserved
    Given LiteFS settings with:
      | field           | value                    |
      | mount_path      | /mnt/lite-fs_data        |
      | data_path       | /var/lib/litefs.d        |
      | database_name   | my_app.sqlite3           |
      | leader_election | static                   |
      | proxy_addr      | :8080                    |
    When I generate the configuration
    Then the YAML should contain fuse.dir "/mnt/lite-fs_data"
    And the YAML should contain data.dir "/var/lib/litefs.d"
    And the YAML should contain databases[0].path "my_app.sqlite3"

  # ---------------------------------------------------------------------------
  # Determinism
  # ---------------------------------------------------------------------------

  Scenario: Same settings produce identical output
    Given LiteFS settings with:
      | field           | value           |
      | mount_path      | /mnt/litefs     |
      | data_path       | /var/lib/litefs |
      | database_name   | db.sqlite3      |
      | leader_election | static          |
      | proxy_addr      | :8080           |
    When I generate the configuration twice
    Then both outputs should be identical
