"""Tests for FastAPI routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.liveness_checker import LivenessChecker
from litefs.usecases.readiness_checker import ReadinessChecker
from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs.usecases.failover_coordinator import NodeState
from litefs_fastapi.routes import create_health_router

from .fakes import (
    FakePrimaryDetector,
    FakeSplitBrainDetectorPort,
    FakeHealthChecker,
    FakeFailoverCoordinator,
    FakeSplitBrainDetector,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_primary_detector() -> FakePrimaryDetector:
    """Create a fake PrimaryDetector."""
    return FakePrimaryDetector(is_primary=True)


@pytest.fixture
def fake_split_brain_detector_port() -> FakeSplitBrainDetectorPort:
    """Create a fake SplitBrainDetectorPort with healthy cluster."""
    return FakeSplitBrainDetectorPort(
        cluster_state=RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=False),
            ]
        )
    )


@pytest.fixture
def health_checker(fake_primary_detector: FakePrimaryDetector) -> HealthChecker:
    """Create a HealthChecker instance for testing."""
    return HealthChecker(
        primary_detector=fake_primary_detector,
        degraded=False,
        unhealthy=False,
    )


@pytest.fixture
def split_brain_detector(
    fake_split_brain_detector_port: FakeSplitBrainDetectorPort,
) -> SplitBrainDetector:
    """Create a SplitBrainDetector instance for testing."""
    return SplitBrainDetector(port=fake_split_brain_detector_port)


@pytest.fixture
def liveness_checker(fake_primary_detector: FakePrimaryDetector) -> LivenessChecker:
    """Create a LivenessChecker instance for testing."""
    return LivenessChecker(primary_detector=fake_primary_detector)


@pytest.fixture
def fake_health_checker() -> FakeHealthChecker:
    """Create a FakeHealthChecker for ReadinessChecker tests."""
    return FakeHealthChecker(health_status="healthy")


@pytest.fixture
def fake_failover_coordinator() -> FakeFailoverCoordinator:
    """Create a FakeFailoverCoordinator for ReadinessChecker tests."""
    return FakeFailoverCoordinator(node_state=NodeState.PRIMARY)


@pytest.fixture
def fake_split_brain_detector_for_readiness() -> FakeSplitBrainDetector:
    """Create a FakeSplitBrainDetector for ReadinessChecker tests."""
    return FakeSplitBrainDetector(is_split_brain=False)


@pytest.fixture
def readiness_checker(
    fake_health_checker: FakeHealthChecker,
    fake_failover_coordinator: FakeFailoverCoordinator,
    fake_split_brain_detector_for_readiness: FakeSplitBrainDetector,
) -> ReadinessChecker:
    """Create a ReadinessChecker instance for testing."""
    return ReadinessChecker(
        health_checker=fake_health_checker,
        failover_coordinator=fake_failover_coordinator,
        split_brain_detector=fake_split_brain_detector_for_readiness,
    )


@pytest.fixture
def test_app(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> FastAPI:
    """Create a test FastAPI app with health router."""
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for the test app."""
    return TestClient(test_app)


# =============================================================================
# Health Endpoint Tests (/health)
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_returns_200_ok(client: TestClient) -> None:
    """Test that health endpoint returns 200 OK status."""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_includes_split_brain_status(client: TestClient) -> None:
    """Test that response includes is_split_brain field."""
    response = client.get("/health")
    data = response.json()
    assert "is_split_brain" in data
    assert isinstance(data["is_split_brain"], bool)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_includes_leader_nodes(client: TestClient) -> None:
    """Test that response includes leader_nodes list."""
    response = client.get("/health")
    data = response.json()
    assert "leader_nodes" in data
    assert isinstance(data["leader_nodes"], list)
    # Default fixture has one leader
    assert len(data["leader_nodes"]) == 1
    assert data["leader_nodes"][0]["node_id"] == "node-1"
    assert data["leader_nodes"][0]["is_leader"] is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_includes_health_status(client: TestClient) -> None:
    """Test that response includes health state field."""
    response = client.get("/health")
    data = response.json()
    assert "health_state" in data
    assert data["health_state"] in ("healthy", "unhealthy", "degraded")


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_with_split_brain_detected(
    health_checker: HealthChecker,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> None:
    """Test endpoint response when split-brain is detected."""
    # Configure split-brain: two leaders
    split_brain_port = FakeSplitBrainDetectorPort(
        cluster_state=RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=True),
                RaftNodeState(node_id="node-3", is_leader=False),
            ]
        )
    )

    split_brain_detector = SplitBrainDetector(port=split_brain_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["is_split_brain"] is True
    assert len(data["leader_nodes"]) == 2
    assert data["leader_nodes"][0]["node_id"] == "node-1"
    assert data["leader_nodes"][1]["node_id"] == "node-2"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_with_no_split_brain(
    health_checker: HealthChecker,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> None:
    """Test endpoint response when cluster is healthy (no split-brain)."""
    # Healthy: one leader
    healthy_port = FakeSplitBrainDetectorPort(
        cluster_state=RaftClusterState(
            nodes=[
                RaftNodeState(node_id="node-1", is_leader=True),
                RaftNodeState(node_id="node-2", is_leader=False),
            ]
        )
    )

    split_brain_detector = SplitBrainDetector(port=healthy_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["is_split_brain"] is False
    assert len(data["leader_nodes"]) == 1
    assert data["health_state"] == "healthy"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_with_degraded_health(
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> None:
    """Test endpoint response with degraded health status."""
    fake_detector = FakePrimaryDetector(is_primary=True)
    health_checker = HealthChecker(
        primary_detector=fake_detector,
        degraded=True,
        unhealthy=False,
    )
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["health_state"] == "degraded"
    assert data["is_split_brain"] is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_health_endpoint_with_unhealthy_status(
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> None:
    """Test endpoint response with unhealthy status."""
    fake_detector = FakePrimaryDetector(is_primary=True)
    health_checker = HealthChecker(
        primary_detector=fake_detector,
        degraded=False,
        unhealthy=True,
    )
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["health_state"] == "unhealthy"
    assert data["is_split_brain"] is False


# =============================================================================
# Liveness Endpoint Tests (/health/live)
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_liveness_returns_200_when_live(client: TestClient) -> None:
    """Test that liveness endpoint returns 200 when LiteFS is running."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["is_live"] is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_liveness_returns_503_when_not_live(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    readiness_checker: ReadinessChecker,
) -> None:
    """Test that liveness endpoint returns 503 when LiteFS is not running."""
    # Create detector that simulates LiteFS not running
    fake_detector = FakePrimaryDetector(is_primary=True)
    fake_detector.set_litefs_not_running()

    liveness_checker = LivenessChecker(primary_detector=fake_detector)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/live")
    assert response.status_code == 503
    data = response.json()
    assert data["is_live"] is False
    assert "error" in data


# =============================================================================
# Readiness Endpoint Tests (/health/ready)
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_returns_200_when_ready(client: TestClient) -> None:
    """Test that readiness endpoint returns 200 when node is ready."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["is_ready"] is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_returns_503_when_not_ready(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
) -> None:
    """Test that readiness endpoint returns 503 when node is not ready."""
    # Create unhealthy state - PRIMARY must be healthy to be ready
    fake_health = FakeHealthChecker(health_status="unhealthy")
    fake_coordinator = FakeFailoverCoordinator(node_state=NodeState.PRIMARY)
    fake_split_brain = FakeSplitBrainDetector(is_split_brain=False)

    readiness_checker = ReadinessChecker(
        health_checker=fake_health,
        failover_coordinator=fake_coordinator,
        split_brain_detector=fake_split_brain,
    )

    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["is_ready"] is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_includes_can_accept_writes(client: TestClient) -> None:
    """Test that readiness response includes can_accept_writes field."""
    response = client.get("/health/ready")
    data = response.json()
    assert "can_accept_writes" in data
    assert isinstance(data["can_accept_writes"], bool)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_includes_health_status(client: TestClient) -> None:
    """Test that readiness response includes health_status field."""
    response = client.get("/health/ready")
    data = response.json()
    assert "health_status" in data
    assert data["health_status"] in ("healthy", "degraded", "unhealthy")


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_primary_can_accept_writes_when_healthy(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
) -> None:
    """Test that a healthy PRIMARY node can accept writes."""
    fake_health = FakeHealthChecker(health_status="healthy")
    fake_coordinator = FakeFailoverCoordinator(node_state=NodeState.PRIMARY)
    fake_split_brain = FakeSplitBrainDetector(is_split_brain=False)

    readiness_checker = ReadinessChecker(
        health_checker=fake_health,
        failover_coordinator=fake_coordinator,
        split_brain_detector=fake_split_brain,
    )

    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/ready")
    data = response.json()
    assert data["is_ready"] is True
    assert data["can_accept_writes"] is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_readiness_replica_cannot_accept_writes(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
) -> None:
    """Test that a REPLICA node cannot accept writes."""
    fake_health = FakeHealthChecker(health_status="healthy")
    fake_coordinator = FakeFailoverCoordinator(node_state=NodeState.REPLICA)
    fake_split_brain = FakeSplitBrainDetector(is_split_brain=False)

    readiness_checker = ReadinessChecker(
        health_checker=fake_health,
        failover_coordinator=fake_coordinator,
        split_brain_detector=fake_split_brain,
    )

    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker,
        split_brain_detector=split_brain_detector,
        liveness_checker=liveness_checker,
        readiness_checker=readiness_checker,
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/ready")
    data = response.json()
    assert data["is_ready"] is True  # Replica can still be ready for reads
    assert data["can_accept_writes"] is False
