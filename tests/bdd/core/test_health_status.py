"""Step definitions for health status feature."""

import pytest
from dataclasses import FrozenInstanceError
from pytest_bdd import scenario, given, when, then, parsers
from unittest.mock import Mock

from litefs.domain.health import HealthStatus
from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.health_checker import HealthChecker
from litefs.adapters.ports import PrimaryDetectorPort


# Scenarios - link to feature file
# BDD tests are tier 1 (unit-level, no external dependencies)


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.HealthChecker")
@scenario(
    "../../features/core/health_status.feature",
    "Node is healthy by default",
)
def test_healthy_by_default():
    """Test that node is healthy when no flags are set."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.HealthChecker")
@scenario(
    "../../features/core/health_status.feature",
    "Node is degraded when degraded flag is set",
)
def test_degraded_when_flag_set():
    """Test that node is degraded when degraded flag is true."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.HealthChecker")
@scenario(
    "../../features/core/health_status.feature",
    "Node is unhealthy when unhealthy flag is set",
)
def test_unhealthy_when_flag_set():
    """Test that node is unhealthy when unhealthy flag is true."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.HealthChecker")
@scenario(
    "../../features/core/health_status.feature",
    "Unhealthy takes precedence over degraded",
)
def test_unhealthy_precedence():
    """Test that unhealthy takes precedence over degraded."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.HealthChecker")
@scenario(
    "../../features/core/health_status.feature",
    "Degraded takes precedence over healthy",
)
def test_degraded_precedence():
    """Test that degraded takes precedence over healthy."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.HealthStatus")
@scenario(
    "../../features/core/health_status.feature",
    "HealthStatus rejects invalid state values",
)
def test_invalid_state_rejected():
    """Test that invalid health state values are rejected."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.HealthStatus")
@scenario(
    "../../features/core/health_status.feature",
    "HealthStatus accepts healthy state",
)
def test_healthy_state_valid():
    """Test that healthy state is valid."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.HealthStatus")
@scenario(
    "../../features/core/health_status.feature",
    "HealthStatus accepts degraded state",
)
def test_degraded_state_valid():
    """Test that degraded state is valid."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.HealthStatus")
@scenario(
    "../../features/core/health_status.feature",
    "HealthStatus accepts unhealthy state",
)
def test_unhealthy_state_valid():
    """Test that unhealthy state is valid."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.HealthStatus")
@scenario(
    "../../features/core/health_status.feature",
    "HealthStatus is immutable",
)
def test_immutability():
    """Test that HealthStatus is immutable."""
    pass


# Fixtures


@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


@pytest.fixture
def mock_primary_detector():
    """Create a mock primary detector for testing."""
    detector = Mock(spec=PrimaryDetectorPort)
    detector.is_primary.return_value = True
    return detector


# Given steps - HealthChecker


@given("a health checker with no flags set")
def health_checker_no_flags(mock_primary_detector: Mock, context: dict):
    """Create a health checker with default flags (all False)."""
    context["health_checker"] = HealthChecker(
        primary_detector=mock_primary_detector,
        degraded=False,
        unhealthy=False,
    )


@given("a health checker with degraded flag set to true")
def health_checker_degraded(mock_primary_detector: Mock, context: dict):
    """Create a health checker with degraded flag set."""
    context["health_checker"] = HealthChecker(
        primary_detector=mock_primary_detector,
        degraded=True,
        unhealthy=False,
    )


@given("a health checker with unhealthy flag set to true")
def health_checker_unhealthy(mock_primary_detector: Mock, context: dict):
    """Create a health checker with unhealthy flag set."""
    context["health_checker"] = HealthChecker(
        primary_detector=mock_primary_detector,
        degraded=False,
        unhealthy=True,
    )


@given("the unhealthy flag is also set to true")
def add_unhealthy_flag(mock_primary_detector: Mock, context: dict):
    """Update health checker to also have unhealthy flag."""
    context["health_checker"] = HealthChecker(
        primary_detector=mock_primary_detector,
        degraded=True,
        unhealthy=True,
    )


@given("the unhealthy flag is set to false")
def unhealthy_flag_false(context: dict):
    """Ensure unhealthy flag is false (already the case from degraded step)."""
    # The health checker was already created with unhealthy=False
    pass


# Given steps - HealthStatus


@given(parsers.parse('a HealthStatus with state "{state}"'))
def given_health_status(context: dict, state: str):
    """Create a HealthStatus with the given state."""
    context["health_status"] = HealthStatus(state=state)  # type: ignore


# When steps


@when("I check the health status")
def check_health_status(context: dict):
    """Execute health check."""
    health_checker = context["health_checker"]
    context["result"] = health_checker.check_health()


@when(parsers.parse('I create a HealthStatus with state "{state}"'))
def create_health_status(context: dict, state: str):
    """Attempt to create a HealthStatus with the given state."""
    try:
        context["health_status"] = HealthStatus(state=state)  # type: ignore
        context["error"] = None
    except LiteFSConfigError as e:
        context["health_status"] = None
        context["error"] = e


@when("I attempt to modify the state")
def attempt_modify_state(context: dict):
    """Attempt to modify the frozen dataclass."""
    health_status = context["health_status"]
    try:
        health_status.state = "unhealthy"  # type: ignore
        context["error"] = None
    except FrozenInstanceError as e:
        context["error"] = e


# Then steps


@then(parsers.parse('the health status should be "{expected_state}"'))
def health_status_is(context: dict, expected_state: str):
    """Assert health status matches expected state."""
    result = context["result"]
    assert result.state == expected_state, f"Expected {expected_state}, got {result.state}"


@then("a LiteFSConfigError should be raised")
def config_error_raised(context: dict):
    """Assert that LiteFSConfigError was raised."""
    assert context["error"] is not None, "Expected LiteFSConfigError but no error was raised"
    assert isinstance(context["error"], LiteFSConfigError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None
    assert text in str(context["error"]), f"Expected '{text}' in '{context['error']}'"


@then("the HealthStatus should be valid")
def health_status_valid(context: dict):
    """Assert HealthStatus was created successfully."""
    assert context["error"] is None, f"Unexpected error: {context['error']}"
    assert context["health_status"] is not None


@then("a FrozenInstanceError should be raised")
def frozen_error_raised(context: dict):
    """Assert that FrozenInstanceError was raised."""
    assert context["error"] is not None, "Expected FrozenInstanceError but no error was raised"
    assert isinstance(context["error"], FrozenInstanceError)
