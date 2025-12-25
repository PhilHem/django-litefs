"""Tests for FastAPI routes."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs_fastapi.routes import create_health_router


@pytest.fixture
def fake_primary_detector_port() -> Mock:
    """Create a fake PrimaryDetectorPort."""
    port = Mock()
    port.is_primary.return_value = True
    return port


@pytest.fixture
def fake_split_brain_detector_port() -> Mock:
    """Create a fake SplitBrainDetectorPort."""
    port = Mock()
    # Default: healthy cluster with single leader
    healthy_state = RaftClusterState(
        nodes=[
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=False),
        ]
    )
    port.get_cluster_state.return_value = healthy_state
    return port


@pytest.fixture
def health_checker(fake_primary_detector_port: Mock) -> HealthChecker:
    """Create a HealthChecker instance for testing."""
    return HealthChecker(
        primary_detector=fake_primary_detector_port,
        degraded=False,
        unhealthy=False,
    )


@pytest.fixture
def split_brain_detector(fake_split_brain_detector_port: Mock) -> SplitBrainDetector:
    """Create a SplitBrainDetector instance for testing."""
    return SplitBrainDetector(port=fake_split_brain_detector_port)


@pytest.fixture
def test_app(
    health_checker: HealthChecker, split_brain_detector: SplitBrainDetector
) -> FastAPI:
    """Create a test FastAPI app with health router."""
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker, split_brain_detector=split_brain_detector
    )
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for the test app."""
    return TestClient(test_app)


@pytest.mark.unit
def test_health_endpoint_returns_200_ok(client: TestClient) -> None:
    """Test that health endpoint returns 200 OK status."""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.unit
def test_health_endpoint_includes_split_brain_status(client: TestClient) -> None:
    """Test that response includes is_split_brain field."""
    response = client.get("/health")
    data = response.json()
    assert "is_split_brain" in data
    assert isinstance(data["is_split_brain"], bool)


@pytest.mark.unit
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


@pytest.mark.unit
def test_health_endpoint_includes_health_status(client: TestClient) -> None:
    """Test that response includes health state field."""
    response = client.get("/health")
    data = response.json()
    assert "health_state" in data
    assert data["health_state"] in ("healthy", "unhealthy", "degraded")


@pytest.mark.unit
def test_health_endpoint_with_split_brain_detected(
    health_checker: HealthChecker, fake_split_brain_detector_port: Mock
) -> None:
    """Test endpoint response when split-brain is detected."""
    # Configure split-brain: two leaders
    split_brain_state = RaftClusterState(
        nodes=[
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=True),
            RaftNodeState(node_id="node-3", is_leader=False),
        ]
    )
    fake_split_brain_detector_port.get_cluster_state.return_value = split_brain_state

    split_brain_detector = SplitBrainDetector(port=fake_split_brain_detector_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker, split_brain_detector=split_brain_detector
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


@pytest.mark.unit
def test_health_endpoint_with_no_split_brain(
    health_checker: HealthChecker, fake_split_brain_detector_port: Mock
) -> None:
    """Test endpoint response when cluster is healthy (no split-brain)."""
    # Healthy: one leader
    healthy_state = RaftClusterState(
        nodes=[
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=False),
        ]
    )
    fake_split_brain_detector_port.get_cluster_state.return_value = healthy_state

    split_brain_detector = SplitBrainDetector(port=fake_split_brain_detector_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker, split_brain_detector=split_brain_detector
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["is_split_brain"] is False
    assert len(data["leader_nodes"]) == 1
    assert data["health_state"] == "healthy"


@pytest.mark.unit
def test_health_endpoint_with_degraded_health(
    fake_primary_detector_port: Mock, fake_split_brain_detector_port: Mock
) -> None:
    """Test endpoint response with degraded health status."""
    health_checker = HealthChecker(
        primary_detector=fake_primary_detector_port,
        degraded=True,
        unhealthy=False,
    )
    split_brain_detector = SplitBrainDetector(port=fake_split_brain_detector_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker, split_brain_detector=split_brain_detector
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["health_state"] == "degraded"
    assert data["is_split_brain"] is False


@pytest.mark.unit
def test_health_endpoint_with_unhealthy_status(
    fake_primary_detector_port: Mock, fake_split_brain_detector_port: Mock
) -> None:
    """Test endpoint response with unhealthy status."""
    health_checker = HealthChecker(
        primary_detector=fake_primary_detector_port,
        degraded=False,
        unhealthy=True,
    )
    split_brain_detector = SplitBrainDetector(port=fake_split_brain_detector_port)
    app = FastAPI()
    router = create_health_router(
        health_checker=health_checker, split_brain_detector=split_brain_detector
    )
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert data["health_state"] == "unhealthy"
    assert data["is_split_brain"] is False
