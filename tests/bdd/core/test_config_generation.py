"""Step definitions for LiteFS configuration generation feature."""

import pytest
import yaml
from pytest_bdd import scenario, given, when, then, parsers

from litefs.domain.settings import LiteFSSettings, ProxySettings
from litefs.usecases.config_generator import ConfigGenerator


# ---------------------------------------------------------------------------
# Scenarios - Basic Configuration Generation
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Minimal configuration is generated correctly",
)
def test_minimal_config():
    """Test minimal configuration generation."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Configuration with raft leader election",
)
def test_raft_config():
    """Test raft leader election configuration."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Proxy Configuration
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Configuration without detailed proxy settings",
)
def test_proxy_addr_only():
    """Test configuration with proxy addr only."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Configuration with detailed proxy settings",
)
def test_detailed_proxy():
    """Test configuration with detailed proxy settings."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - YAML Output Validity
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Generated configuration is valid YAML",
)
def test_valid_yaml():
    """Test generated configuration is valid YAML."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Generated configuration uses block style YAML",
)
def test_block_style():
    """Test generated configuration uses block style."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Path Handling
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Paths with special characters are preserved",
)
def test_special_chars():
    """Test paths with special characters are preserved."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Determinism
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.ConfigGenerator")
@scenario(
    "../../features/core/config_generation.feature",
    "Same settings produce identical output",
)
def test_determinism():
    """Test same settings produce identical output."""
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


@pytest.fixture
def config_generator():
    """Create ConfigGenerator instance."""
    return ConfigGenerator()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("LiteFS settings with:")
def settings_from_table(context: dict, datatable):
    """Create LiteFS settings from datatable.

    Note: datatable is a list of lists where first row is headers.
    """
    # Parse datatable into dict
    settings_dict = {}
    for row in datatable[1:]:
        field = row[0]
        value = row[1]
        settings_dict[field] = value

    # Create settings with required fields
    context["settings"] = LiteFSSettings(
        mount_path=settings_dict.get("mount_path", "/mnt/litefs"),
        data_path=settings_dict.get("data_path", "/var/lib/litefs"),
        database_name=settings_dict.get("database_name", "db.sqlite3"),
        leader_election=settings_dict.get("leader_election", "static"),
        proxy_addr=settings_dict.get("proxy_addr", ":8080"),
        enabled=True,
        retention="1h",
        # Raft settings if leader_election is raft
        raft_self_addr=(
            settings_dict.get("raft_self_addr", "node1:20202")
            if settings_dict.get("leader_election") == "raft"
            else None
        ),
        raft_peers=(
            ["node2:20202", "node3:20202"]
            if settings_dict.get("leader_election") == "raft"
            else None
        ),
    )


@given(parsers.parse('LiteFS settings with proxy_addr "{proxy_addr}" only'))
def settings_proxy_addr_only(context: dict, proxy_addr: str):
    """Create LiteFS settings with only proxy_addr (no detailed proxy)."""
    context["settings"] = LiteFSSettings(
        mount_path="/mnt/litefs",
        data_path="/var/lib/litefs",
        database_name="db.sqlite3",
        leader_election="static",
        proxy_addr=proxy_addr,
        enabled=True,
        retention="1h",
        proxy=None,  # No detailed proxy settings
    )


@given("LiteFS settings with proxy settings:")
def settings_with_proxy(context: dict, datatable):
    """Create LiteFS settings with detailed proxy settings."""
    # Parse datatable into dict
    proxy_dict = {}
    for row in datatable[1:]:
        field = row[0]
        value = row[1]
        proxy_dict[field] = value

    # Create ProxySettings
    proxy = ProxySettings(
        addr=":8080",
        target=proxy_dict.get("target", "localhost:8081"),
        db=proxy_dict.get("db", "db.sqlite3"),
        passthrough=[proxy_dict.get("passthrough", "/static/*")],
        primary_redirect_timeout=proxy_dict.get("primary_redirect_timeout", "5s"),
    )

    context["settings"] = LiteFSSettings(
        mount_path="/mnt/litefs",
        data_path="/var/lib/litefs",
        database_name="db.sqlite3",
        leader_election="static",
        proxy_addr=":8080",
        enabled=True,
        retention="1h",
        proxy=proxy,
    )


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("I generate the configuration")
def generate_config(context: dict, config_generator: ConfigGenerator):
    """Generate configuration from settings."""
    settings = context["settings"]
    context["output"] = config_generator.generate(settings)
    context["parsed"] = yaml.safe_load(context["output"])


@when("I generate the configuration twice")
def generate_config_twice(context: dict, config_generator: ConfigGenerator):
    """Generate configuration twice for determinism test."""
    settings = context["settings"]
    context["output1"] = config_generator.generate(settings)
    context["output2"] = config_generator.generate(settings)


# ---------------------------------------------------------------------------
# Then steps - YAML content assertions
# ---------------------------------------------------------------------------


@then(parsers.parse('the YAML should contain fuse.dir "{expected}"'))
def yaml_contains_fuse_dir(context: dict, expected: str):
    """Assert YAML contains fuse.dir value."""
    parsed = context["parsed"]
    assert parsed["fuse"]["dir"] == expected


@then(parsers.parse('the YAML should contain data.dir "{expected}"'))
def yaml_contains_data_dir(context: dict, expected: str):
    """Assert YAML contains data.dir value."""
    parsed = context["parsed"]
    assert parsed["data"]["dir"] == expected


@then(parsers.parse('the YAML should contain databases[0].path "{expected}"'))
def yaml_contains_database_path(context: dict, expected: str):
    """Assert YAML contains databases[0].path value."""
    parsed = context["parsed"]
    assert parsed["databases"][0]["path"] == expected


@then(parsers.parse('the YAML should contain lease.type "{expected}"'))
def yaml_contains_lease_type(context: dict, expected: str):
    """Assert YAML contains lease.type value."""
    parsed = context["parsed"]
    assert parsed["lease"]["type"] == expected


@then(parsers.parse('the YAML should contain proxy.addr "{expected}"'))
def yaml_contains_proxy_addr(context: dict, expected: str):
    """Assert YAML contains proxy.addr value."""
    parsed = context["parsed"]
    assert parsed["proxy"]["addr"] == expected


@then(parsers.parse('the YAML should contain proxy.target "{expected}"'))
def yaml_contains_proxy_target(context: dict, expected: str):
    """Assert YAML contains proxy.target value."""
    parsed = context["parsed"]
    assert parsed["proxy"]["target"] == expected


@then(parsers.parse('the YAML should contain proxy.db "{expected}"'))
def yaml_contains_proxy_db(context: dict, expected: str):
    """Assert YAML contains proxy.db value."""
    parsed = context["parsed"]
    assert parsed["proxy"]["db"] == expected


@then(parsers.parse('the YAML should contain proxy.passthrough "{expected}"'))
def yaml_contains_proxy_passthrough(context: dict, expected: str):
    """Assert YAML contains proxy.passthrough value."""
    parsed = context["parsed"]
    assert expected in parsed["proxy"]["passthrough"]


@then(parsers.parse('the YAML should contain proxy.primary_redirect_timeout "{expected}"'))
def yaml_contains_proxy_timeout(context: dict, expected: str):
    """Assert YAML contains proxy.primary_redirect_timeout value."""
    parsed = context["parsed"]
    assert parsed["proxy"]["primary_redirect_timeout"] == expected


@then("the YAML should NOT contain proxy.target")
def yaml_not_contains_proxy_target(context: dict):
    """Assert YAML does not contain proxy.target."""
    parsed = context["parsed"]
    assert "target" not in parsed["proxy"]


@then("the YAML should NOT contain proxy.db")
def yaml_not_contains_proxy_db(context: dict):
    """Assert YAML does not contain proxy.db."""
    parsed = context["parsed"]
    assert "db" not in parsed["proxy"]


# ---------------------------------------------------------------------------
# Then steps - YAML validity
# ---------------------------------------------------------------------------


@then("the output should be valid YAML")
def output_is_valid_yaml(context: dict):
    """Assert output is valid YAML."""
    output = context["output"]
    try:
        yaml.safe_load(output)
    except yaml.YAMLError as e:
        pytest.fail(f"Output is not valid YAML: {e}")


@then("the output should be parseable back to a dictionary")
def output_parseable_to_dict(context: dict):
    """Assert output can be parsed back to dict."""
    parsed = context["parsed"]
    assert isinstance(parsed, dict)


@then("the output should NOT contain flow style braces")
def output_no_flow_style(context: dict):
    """Assert output uses block style (no braces on same line as key)."""
    output = context["output"]
    # Flow style would have { or [ on same line after :
    # Block style has newline after :
    assert "{" not in output, "Output contains flow style braces"
    # Lists in block style are fine with [ only inside passthrough values
    # But the structure itself should not use flow style


# ---------------------------------------------------------------------------
# Then steps - Determinism
# ---------------------------------------------------------------------------


@then("both outputs should be identical")
def outputs_identical(context: dict):
    """Assert both outputs are identical."""
    assert context["output1"] == context["output2"]
