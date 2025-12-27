"""Step definitions for health_status.feature.

BDD tests for the detailed health status endpoint for operators/monitoring.
TRA Namespace: Contract.HealthStatus
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs.domain.health import HealthStatus  # noqa: E402
from litefs.usecases.failover_coordinator import NodeState  # noqa: E402
from tests.core.unit.fakes.fake_failover_coordinator import (  # noqa: E402
    FakeFailoverCoordinator,
)
from tests.core.unit.fakes.fake_health_checker import FakeHealthChecker  # noqa: E402
from tests.django_adapter.unit.fakes import FakePrimaryDetector  # noqa: E402


# =============================================================================
# Scenarios
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthStatus")
@scenario(
    "../../features/django/health_status.feature",
    "Health endpoint returns complete status for primary",
)
def test_health_endpoint_returns_complete_status_for_primary() -> None:
    """Test health endpoint returns complete status for primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthStatus")
@scenario(
    "../../features/django/health_status.feature",
    "Health endpoint returns complete status for replica",
)
def test_health_endpoint_returns_complete_status_for_replica() -> None:
    """Test health endpoint returns complete status for replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthStatus")
@scenario(
    "../../features/django/health_status.feature",
    "Health endpoint includes error details when LiteFS not running",
)
def test_health_endpoint_includes_error_details_when_litefs_not_running() -> None:
    """Test health endpoint includes error when LiteFS not running."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthStatus")
@scenario(
    "../../features/django/health_status.feature",
    "Health endpoint returns degraded status with details",
)
def test_health_endpoint_returns_degraded_status_with_details() -> None:
    """Test health endpoint returns degraded status with details."""
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared context for passing state between steps."""
    return {
        "fake_primary_detector": None,
        "fake_health_checker": None,
        "fake_failover_coordinator": None,
        "response": None,
        "response_status": None,
    }


@pytest.fixture
def fake_primary_detector() -> FakePrimaryDetector:
    """Create a fake primary detector for testing."""
    return FakePrimaryDetector(is_primary=True)


@pytest.fixture
def fake_health_checker() -> FakeHealthChecker:
    """Create a fake health checker for testing."""
    return FakeHealthChecker()


@pytest.fixture
def fake_failover_coordinator() -> FakeFailoverCoordinator:
    """Create a fake failover coordinator for testing."""
    return FakeFailoverCoordinator(initial_state=NodeState.PRIMARY)


# =============================================================================
# Given Steps
# =============================================================================


@given("the node is the primary")
def node_is_primary(
    context: dict[str, Any],
    fake_primary_detector: FakePrimaryDetector,
    fake_failover_coordinator: FakeFailoverCoordinator,
) -> None:
    """Configure node as primary."""
    fake_primary_detector.set_primary(True)
    fake_failover_coordinator.set_state(NodeState.PRIMARY)
    context["fake_primary_detector"] = fake_primary_detector
    context["fake_failover_coordinator"] = fake_failover_coordinator


@given("the node is a replica")
def node_is_replica(
    context: dict[str, Any],
    fake_primary_detector: FakePrimaryDetector,
    fake_failover_coordinator: FakeFailoverCoordinator,
) -> None:
    """Configure node as replica."""
    fake_primary_detector.set_primary(False)
    fake_failover_coordinator.set_state(NodeState.REPLICA)
    context["fake_primary_detector"] = fake_primary_detector
    context["fake_failover_coordinator"] = fake_failover_coordinator


@given(parsers.parse('the node health status is "{status}"'))
def node_health_status_is(
    context: dict[str, Any],
    fake_health_checker: FakeHealthChecker,
    status: str,
) -> None:
    """Set the node health status."""
    fake_health_checker.set_health_status(HealthStatus(state=status))  # type: ignore[arg-type]
    context["fake_health_checker"] = fake_health_checker


@given("LiteFS is not running on the node")
def litefs_not_running(
    context: dict[str, Any],
    fake_primary_detector: FakePrimaryDetector,
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_health_checker: FakeHealthChecker,
) -> None:
    """Configure LiteFS as not running."""
    fake_primary_detector.set_litefs_not_running()
    fake_failover_coordinator.set_state(NodeState.REPLICA)
    fake_health_checker.set_health_status(HealthStatus(state="unhealthy"))
    context["fake_primary_detector"] = fake_primary_detector
    context["fake_failover_coordinator"] = fake_failover_coordinator
    context["fake_health_checker"] = fake_health_checker


# =============================================================================
# When Steps
# =============================================================================


@when("I request the health endpoint")
def request_health_endpoint(context: dict[str, Any]) -> None:
    """Request the health_check_view and store result."""
    from django.test import RequestFactory

    from litefs_django.views import health_check_view

    fake_primary_detector = context["fake_primary_detector"]
    fake_health_checker = context["fake_health_checker"]
    fake_failover_coordinator = context["fake_failover_coordinator"]

    # Create a mock request
    factory = RequestFactory()
    request = factory.get("/health/")

    # Patch the factory functions to return our fakes
    with (
        patch(
            "litefs_django.views.get_primary_detector",
            return_value=fake_primary_detector,
        ),
        patch(
            "litefs_django.views.get_health_checker",
            return_value=fake_health_checker,
        ),
        patch(
            "litefs_django.views.get_failover_coordinator",
            return_value=fake_failover_coordinator,
        ),
    ):
        response = health_check_view(request)

    context["response"] = response
    context["response_status"] = response.status_code


# =============================================================================
# Then Steps - Response Status
# =============================================================================


@then(parsers.parse("the response status should be {status:d}"))
def response_status_should_be(context: dict[str, Any], status: int) -> None:
    """Assert the response status code."""
    assert context["response_status"] == status, (
        f"Expected status {status}, got {context['response_status']}"
    )


# =============================================================================
# Then Steps - Response Fields
# =============================================================================


@then(parsers.parse('the response should include "is_primary" as {value}'))
def response_includes_is_primary(context: dict[str, Any], value: str) -> None:
    """Assert the is_primary field value."""
    import json

    response = context["response"]
    data = json.loads(response.content)
    expected = value.lower() == "true"
    assert data.get("is_primary") == expected, (
        f"Expected is_primary={expected}, got {data.get('is_primary')}"
    )


@then(parsers.parse('the response should include "health_status" as "{value}"'))
def response_includes_health_status(context: dict[str, Any], value: str) -> None:
    """Assert the health_status field value."""
    import json

    response = context["response"]
    data = json.loads(response.content)
    assert data.get("health_status") == value, (
        f"Expected health_status={value}, got {data.get('health_status')}"
    )


@then(parsers.parse('the response should include "node_state" as "{value}"'))
def response_includes_node_state(context: dict[str, Any], value: str) -> None:
    """Assert the node_state field value."""
    import json

    response = context["response"]
    data = json.loads(response.content)
    assert data.get("node_state") == value, (
        f"Expected node_state={value}, got {data.get('node_state')}"
    )


@then(parsers.parse('the response should include "is_ready" as {value}'))
def response_includes_is_ready(context: dict[str, Any], value: str) -> None:
    """Assert the is_ready field value."""
    import json

    response = context["response"]
    data = json.loads(response.content)
    expected = value.lower() == "true"
    assert data.get("is_ready") == expected, (
        f"Expected is_ready={expected}, got {data.get('is_ready')}"
    )


@then('the response should include "error"')
def response_includes_error(context: dict[str, Any]) -> None:
    """Assert the response includes an error field."""
    import json

    response = context["response"]
    data = json.loads(response.content)
    assert "error" in data, f"Expected 'error' field in response, got {data.keys()}"
    assert data["error"] is not None, "Expected non-None error value"
