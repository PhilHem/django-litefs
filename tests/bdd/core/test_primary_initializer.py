"""Step definitions for primary initializer feature."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from litefs.domain.settings import StaticLeaderConfig
from litefs.usecases.primary_initializer import PrimaryInitializer


# ---------------------------------------------------------------------------
# Scenarios - Happy Path
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Node is primary when hostname matches exactly",
)
def test_primary_exact_match():
    """Test node is primary when hostname matches."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Node is replica when hostname does not match",
)
def test_replica_no_match():
    """Test node is replica when hostname doesn't match."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Case Sensitivity
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Comparison is case-sensitive - uppercase vs lowercase",
)
def test_case_sensitive_upper_lower():
    """Test case-sensitive comparison (uppercase config vs lowercase node)."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Comparison is case-sensitive - lowercase vs uppercase",
)
def test_case_sensitive_lower_upper():
    """Test case-sensitive comparison (lowercase config vs uppercase node)."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - No Partial Matching
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "No prefix matching",
)
def test_no_prefix_match():
    """Test no prefix matching."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "No suffix matching",
)
def test_no_suffix_match():
    """Test no suffix matching."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Hostname Formats
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "FQDN hostnames are supported",
)
def test_fqdn_hostname():
    """Test FQDN hostnames are supported."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "IP addresses are supported",
)
def test_ip_address():
    """Test IP addresses are supported."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Hyphenated hostnames are supported",
)
def test_hyphenated_hostname():
    """Test hyphenated hostnames are supported."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - Statelessness
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryInitializer")
@scenario(
    "../../features/core/primary_initializer.feature",
    "Multiple checks are independent",
)
def test_stateless_checks():
    """Test multiple checks are independent (stateless)."""
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given(parsers.parse('a static leader config with primary_hostname "{hostname}"'))
def given_static_config(context: dict, hostname: str):
    """Create a static leader config with the given primary hostname."""
    config = StaticLeaderConfig(primary_hostname=hostname)
    context["config"] = config
    context["initializer"] = PrimaryInitializer(config=config)


@given(parsers.parse('the current node hostname is "{hostname}"'))
def given_current_hostname(context: dict, hostname: str):
    """Set the current node hostname for checking."""
    context["current_hostname"] = hostname


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("I check if the node is primary")
def check_is_primary(context: dict):
    """Execute primary check."""
    initializer = context["initializer"]
    current_hostname = context["current_hostname"]
    context["result"] = initializer.is_primary(current_hostname)


@when(parsers.parse('I check is_primary with "{hostname}"'))
def check_is_primary_with_hostname(context: dict, hostname: str):
    """Execute primary check with specific hostname."""
    initializer = context["initializer"]
    context["result"] = initializer.is_primary(hostname)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("the result should be true")
def result_is_true(context: dict):
    """Assert result is True."""
    assert context["result"] is True, f"Expected True, got {context['result']}"


@then("the result should be false")
def result_is_false(context: dict):
    """Assert result is False."""
    assert context["result"] is False, f"Expected False, got {context['result']}"
