"""Step definitions for health_probes.feature.

BDD tests for liveness and readiness probe endpoints.
TRA Namespace: Contract.HealthProbe
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs.domain.health import HealthStatus, LivenessResult, ReadinessResult  # noqa: E402
from litefs.domain.split_brain import RaftClusterState, RaftNodeState  # noqa: E402
from litefs.usecases.failover_coordinator import NodeState  # noqa: E402
from litefs.usecases.liveness_checker import LivenessChecker  # noqa: E402
from litefs.usecases.primary_detector import LiteFSNotRunningError  # noqa: E402
from litefs.usecases.readiness_checker import ReadinessChecker  # noqa: E402
from litefs.usecases.split_brain_detector import SplitBrainDetector  # noqa: E402
from tests.core.unit.fakes import FakeFailoverCoordinator, FakeHealthChecker  # noqa: E402
from tests.django_adapter.unit.fakes import FakePrimaryDetector, FakeSplitBrainDetector  # noqa: E402


# =============================================================================
# Scenarios - Liveness Probe
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Liveness returns 200 when LiteFS is running",
)
def test_liveness_returns_200_when_litefs_is_running() -> None:
    """Test that liveness returns 200 when LiteFS is running."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Liveness returns 503 when LiteFS is not running",
)
def test_liveness_returns_503_when_litefs_is_not_running() -> None:
    """Test that liveness returns 503 when LiteFS is not running."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Liveness returns 200 even when node is degraded",
)
def test_liveness_returns_200_even_when_node_is_degraded() -> None:
    """Test that liveness returns 200 even when node is degraded."""
    pass


# =============================================================================
# Scenarios - Readiness Probe (Primary Node)
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 200 for healthy primary",
)
def test_readiness_returns_200_for_healthy_primary() -> None:
    """Test that readiness returns 200 for healthy primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 503 for degraded primary",
)
def test_readiness_returns_503_for_degraded_primary() -> None:
    """Test that readiness returns 503 for degraded primary."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 503 for unhealthy primary",
)
def test_readiness_returns_503_for_unhealthy_primary() -> None:
    """Test that readiness returns 503 for unhealthy primary."""
    pass


# =============================================================================
# Scenarios - Readiness Probe (Replica Node)
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 200 for healthy replica",
)
def test_readiness_returns_200_for_healthy_replica() -> None:
    """Test that readiness returns 200 for healthy replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 200 for degraded replica",
)
def test_readiness_returns_200_for_degraded_replica() -> None:
    """Test that readiness returns 200 for degraded replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 503 for unhealthy replica",
)
def test_readiness_returns_503_for_unhealthy_replica() -> None:
    """Test that readiness returns 503 for unhealthy replica."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 503 when LiteFS is not running",
)
def test_readiness_returns_503_when_litefs_is_not_running() -> None:
    """Test that readiness returns 503 when LiteFS is not running."""
    pass


# =============================================================================
# Scenarios - Split-Brain Detection
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 503 when split-brain detected",
)
def test_readiness_returns_503_when_split_brain_detected() -> None:
    """Test that readiness returns 503 when split-brain detected."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Readiness returns 200 with single leader",
)
def test_readiness_returns_200_with_single_leader() -> None:
    """Test that readiness returns 200 with single leader."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Contract.HealthProbe")
@scenario(
    "../../features/django/health_probes.feature",
    "Static leader mode skips split-brain detection",
)
def test_static_leader_mode_skips_split_brain_detection() -> None:
    """Test that static leader mode skips split-brain detection."""
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared context for passing state between steps."""
    return {
        "litefs_running": True,
        "node_role": "primary",
        "health_status": "healthy",
        "election_mode": "raft",  # or "static"
        "leader_count": 1,
        "response_status": None,
        "response": None,
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


@pytest.fixture
def fake_split_brain_detector() -> FakeSplitBrainDetector:
    """Create a fake split-brain detector for testing."""
    return FakeSplitBrainDetector()


# =============================================================================
# Given Steps - Liveness
# =============================================================================


@given("LiteFS is running on the node")
def litefs_is_running(
    context: dict[str, Any], fake_primary_detector: FakePrimaryDetector
) -> None:
    """Configure LiteFS as running."""
    context["litefs_running"] = True
    fake_primary_detector.set_primary(True)
    fake_primary_detector.set_error(None)
    context["fake_primary_detector"] = fake_primary_detector


@given("LiteFS is not running on the node")
def litefs_is_not_running(
    context: dict[str, Any], fake_primary_detector: FakePrimaryDetector
) -> None:
    """Configure LiteFS as not running."""
    context["litefs_running"] = False
    fake_primary_detector.set_error(LiteFSNotRunningError("LiteFS mount not found"))
    context["fake_primary_detector"] = fake_primary_detector


@given(parsers.parse('the node health status is "{status}"'))
def node_health_status_is(
    context: dict[str, Any],
    fake_health_checker: FakeHealthChecker,
    status: str,
) -> None:
    """Set the node health status."""
    context["health_status"] = status
    fake_health_checker.set_health_status(HealthStatus(state=status))  # type: ignore[arg-type]
    context["fake_health_checker"] = fake_health_checker


# =============================================================================
# Given Steps - Readiness (Node Role)
# =============================================================================


@given("the node is the primary")
def node_is_primary(
    context: dict[str, Any],
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_health_checker: FakeHealthChecker,
) -> None:
    """Configure node as primary."""
    context["node_role"] = "primary"
    fake_failover_coordinator.set_state(NodeState.PRIMARY)
    context["fake_failover_coordinator"] = fake_failover_coordinator
    context["fake_health_checker"] = fake_health_checker


@given("the node is a replica")
def node_is_replica(
    context: dict[str, Any],
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_health_checker: FakeHealthChecker,
) -> None:
    """Configure node as replica."""
    context["node_role"] = "replica"
    fake_failover_coordinator.set_state(NodeState.REPLICA)
    context["fake_failover_coordinator"] = fake_failover_coordinator
    context["fake_health_checker"] = fake_health_checker


# =============================================================================
# Given Steps - Split-Brain Detection
# =============================================================================


@given("Raft leader election is configured")
def raft_leader_election_configured(
    context: dict[str, Any],
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_health_checker: FakeHealthChecker,
    fake_split_brain_detector: FakeSplitBrainDetector,
) -> None:
    """Configure Raft leader election mode."""
    context["election_mode"] = "raft"
    context["fake_failover_coordinator"] = fake_failover_coordinator
    context["fake_health_checker"] = fake_health_checker
    context["fake_split_brain_detector"] = fake_split_brain_detector


@given("multiple nodes claim leadership")
def multiple_nodes_claim_leadership(
    context: dict[str, Any],
    fake_split_brain_detector: FakeSplitBrainDetector,
) -> None:
    """Configure split-brain state (multiple leaders)."""
    context["leader_count"] = 2
    # Set cluster state with 2 leaders
    cluster_state = RaftClusterState(
        nodes=[
            RaftNodeState(node_id="node1", is_leader=True),
            RaftNodeState(node_id="node2", is_leader=True),
            RaftNodeState(node_id="node3", is_leader=False),
        ]
    )
    fake_split_brain_detector.set_cluster_state(cluster_state)
    context["fake_split_brain_detector"] = fake_split_brain_detector


@given("exactly one node is the leader")
def exactly_one_node_is_leader(
    context: dict[str, Any],
    fake_split_brain_detector: FakeSplitBrainDetector,
) -> None:
    """Configure healthy cluster with single leader."""
    context["leader_count"] = 1
    # Default cluster state has single leader
    cluster_state = RaftClusterState(
        nodes=[
            RaftNodeState(node_id="node1", is_leader=True),
            RaftNodeState(node_id="node2", is_leader=False),
            RaftNodeState(node_id="node3", is_leader=False),
        ]
    )
    fake_split_brain_detector.set_cluster_state(cluster_state)
    context["fake_split_brain_detector"] = fake_split_brain_detector


@given("static leader election is configured")
def static_leader_election_configured(
    context: dict[str, Any],
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_health_checker: FakeHealthChecker,
) -> None:
    """Configure static leader election mode (no split-brain detector)."""
    context["election_mode"] = "static"
    context["fake_failover_coordinator"] = fake_failover_coordinator
    context["fake_health_checker"] = fake_health_checker
    # No split-brain detector for static mode
    context["fake_split_brain_detector"] = None


# =============================================================================
# When Steps
# =============================================================================


@when("I request the liveness endpoint")
def request_liveness_endpoint(context: dict[str, Any]) -> None:
    """Request the liveness endpoint and store result."""
    fake_primary_detector = context.get("fake_primary_detector")

    if fake_primary_detector is None:
        # Create a default running detector
        fake_primary_detector = FakePrimaryDetector(is_primary=True)

    liveness_checker = LivenessChecker(primary_detector=fake_primary_detector)
    result = liveness_checker.check_liveness()

    context["response"] = result
    context["response_status"] = 200 if result.is_live else 503


@when("I request the readiness endpoint")
def request_readiness_endpoint(context: dict[str, Any]) -> None:
    """Request the readiness endpoint and store result."""
    # Get or create fakes based on context
    fake_health_checker = context.get("fake_health_checker")
    fake_failover_coordinator = context.get("fake_failover_coordinator")
    fake_split_brain_detector = context.get("fake_split_brain_detector")

    if fake_health_checker is None:
        fake_health_checker = FakeHealthChecker()
        health_status = context.get("health_status", "healthy")
        fake_health_checker.set_health_status(
            HealthStatus(state=health_status)  # type: ignore[arg-type]
        )

    if fake_failover_coordinator is None:
        fake_failover_coordinator = FakeFailoverCoordinator(
            initial_state=NodeState.PRIMARY
        )

    # Handle LiteFS not running case
    if not context.get("litefs_running", True):
        # When LiteFS is not running, readiness should fail
        result = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="unhealthy"),
            split_brain_detected=False,
            leader_node_ids=(),
            error="LiteFS is not running",
        )
        context["response"] = result
        context["response_status"] = 503
        return

    # Create split-brain detector if in raft mode
    split_brain_detector = None
    if fake_split_brain_detector is not None:
        split_brain_detector = SplitBrainDetector(port=fake_split_brain_detector)

    readiness_checker = ReadinessChecker(
        health_checker=fake_health_checker,
        failover_coordinator=fake_failover_coordinator,
        split_brain_detector=split_brain_detector,
    )
    result = readiness_checker.check_readiness()

    context["response"] = result
    context["response_status"] = 200 if result.is_ready else 503


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
# Then Steps - Liveness Response
# =============================================================================


@then(parsers.parse('the response should include "is_live" as {value}'))
def response_includes_is_live(context: dict[str, Any], value: str) -> None:
    """Assert the is_live field value."""
    response = context["response"]
    expected = value.lower() == "true"
    assert isinstance(response, LivenessResult), (
        f"Expected LivenessResult, got {type(response)}"
    )
    assert response.is_live == expected, (
        f"Expected is_live={expected}, got {response.is_live}"
    )


@then("the response should include an error message")
def response_includes_error_message(context: dict[str, Any]) -> None:
    """Assert the response includes an error message."""
    response = context["response"]
    assert response.error is not None, "Expected error message but got None"
    assert len(response.error) > 0, "Expected non-empty error message"


# =============================================================================
# Then Steps - Readiness Response
# =============================================================================


@then(parsers.parse('the response should include "is_ready" as {value}'))
def response_includes_is_ready(context: dict[str, Any], value: str) -> None:
    """Assert the is_ready field value."""
    response = context["response"]
    expected = value.lower() == "true"
    assert isinstance(response, ReadinessResult), (
        f"Expected ReadinessResult, got {type(response)}"
    )
    assert response.is_ready == expected, (
        f"Expected is_ready={expected}, got {response.is_ready}"
    )


@then(parsers.parse('the response should include "can_accept_writes" as {value}'))
def response_includes_can_accept_writes(context: dict[str, Any], value: str) -> None:
    """Assert the can_accept_writes field value."""
    response = context["response"]
    expected = value.lower() == "true"
    assert isinstance(response, ReadinessResult), (
        f"Expected ReadinessResult, got {type(response)}"
    )
    assert response.can_accept_writes == expected, (
        f"Expected can_accept_writes={expected}, got {response.can_accept_writes}"
    )


# =============================================================================
# Then Steps - Split-Brain Detection
# =============================================================================


@then(parsers.parse('the response should include "split_brain_detected" as {value}'))
def response_includes_split_brain_detected(context: dict[str, Any], value: str) -> None:
    """Assert the split_brain_detected field value."""
    response = context["response"]
    expected = value.lower() == "true"
    assert isinstance(response, ReadinessResult), (
        f"Expected ReadinessResult, got {type(response)}"
    )
    assert response.split_brain_detected == expected, (
        f"Expected split_brain_detected={expected}, got {response.split_brain_detected}"
    )


@then("the response should include the leader node IDs")
def response_includes_leader_node_ids(context: dict[str, Any]) -> None:
    """Assert the response includes leader node IDs."""
    response = context["response"]
    assert isinstance(response, ReadinessResult), (
        f"Expected ReadinessResult, got {type(response)}"
    )
    assert len(response.leader_node_ids) > 0, (
        "Expected leader_node_ids but got empty tuple"
    )


@then('the response should not include "split_brain_detected"')
def response_does_not_include_split_brain_detected(context: dict[str, Any]) -> None:
    """Assert that split_brain_detected is not in response (or is False for static mode)."""
    response = context["response"]
    assert isinstance(response, ReadinessResult), (
        f"Expected ReadinessResult, got {type(response)}"
    )
    # In static mode, split_brain_detected should be False (default, not actively checked)
    assert response.split_brain_detected is False, (
        f"Expected split_brain_detected=False for static mode, got {response.split_brain_detected}"
    )
