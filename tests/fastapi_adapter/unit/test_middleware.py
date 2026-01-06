"""Tests for FastAPI middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from litefs.domain.split_brain import RaftClusterState, RaftNodeState
from litefs.usecases.split_brain_detector import SplitBrainDetector

from .fakes import (
    FakePrimaryDetector,
    FakeSplitBrainDetectorPort,
    FakeSplitBrainDetector,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_app() -> FastAPI:
    """Create a simple FastAPI app for middleware testing."""
    app = FastAPI()

    @app.get("/")
    def root() -> dict:
        return {"status": "ok"}

    @app.post("/write")
    def write_endpoint() -> dict:
        return {"action": "write"}

    @app.get("/read")
    def read_endpoint() -> dict:
        return {"action": "read"}

    return app


@pytest.fixture
def fake_healthy_split_brain_detector() -> FakeSplitBrainDetector:
    """Create a FakeSplitBrainDetector with healthy cluster."""
    return FakeSplitBrainDetector(is_split_brain=False)


@pytest.fixture
def fake_split_brain_detected() -> FakeSplitBrainDetector:
    """Create a FakeSplitBrainDetector with split-brain detected."""
    return FakeSplitBrainDetector(
        is_split_brain=True,
        leader_nodes=[
            RaftNodeState(node_id="node-1", is_leader=True),
            RaftNodeState(node_id="node-2", is_leader=True),
        ],
    )


@pytest.fixture
def fake_primary_detector() -> FakePrimaryDetector:
    """Create a FakePrimaryDetector that reports as primary."""
    return FakePrimaryDetector(is_primary=True)


@pytest.fixture
def fake_replica_detector() -> FakePrimaryDetector:
    """Create a FakePrimaryDetector that reports as replica."""
    return FakePrimaryDetector(is_primary=False)


# =============================================================================
# SplitBrainMiddleware Tests
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_split_brain_middleware_allows_healthy_requests(
    simple_app: FastAPI,
    fake_healthy_split_brain_detector: FakeSplitBrainDetector,
) -> None:
    """Test that middleware allows requests when cluster is healthy."""
    from litefs_fastapi.middleware import SplitBrainMiddleware

    simple_app.add_middleware(
        SplitBrainMiddleware,
        detector=fake_healthy_split_brain_detector,
    )
    client = TestClient(simple_app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_split_brain_middleware_returns_503_on_split_brain(
    simple_app: FastAPI,
    fake_split_brain_detected: FakeSplitBrainDetector,
) -> None:
    """Test that middleware returns 503 when split-brain is detected."""
    from litefs_fastapi.middleware import SplitBrainMiddleware

    simple_app.add_middleware(
        SplitBrainMiddleware,
        detector=fake_split_brain_detected,
    )
    client = TestClient(simple_app)

    response = client.get("/")
    assert response.status_code == 503
    assert "Retry-After" in response.headers
    assert "split-brain" in response.text.lower()


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_split_brain_middleware_fails_open_on_error(
    simple_app: FastAPI,
) -> None:
    """Test that middleware allows requests when detection fails (fail-open)."""
    from litefs_fastapi.middleware import SplitBrainMiddleware

    # Create detector that raises an error
    failing_detector = FakeSplitBrainDetector(is_split_brain=False)
    failing_detector.set_error(RuntimeError("Detection service unavailable"))

    simple_app.add_middleware(
        SplitBrainMiddleware,
        detector=failing_detector,
    )
    client = TestClient(simple_app)

    response = client.get("/")
    # Should allow request through (fail-open)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_split_brain_middleware_ignores_non_http(
    fake_healthy_split_brain_detector: FakeSplitBrainDetector,
) -> None:
    """Test that middleware passes through non-HTTP scopes."""
    from litefs_fastapi.middleware import SplitBrainMiddleware

    # Track if inner app was called
    inner_called = False

    async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal inner_called
        inner_called = True

    middleware = SplitBrainMiddleware(
        app=inner_app,
        detector=fake_healthy_split_brain_detector,
    )

    # Simulate websocket scope (non-HTTP)
    import asyncio

    async def run_test():
        nonlocal inner_called
        scope = {"type": "websocket"}
        await middleware(scope, None, None)  # type: ignore
        return inner_called

    result = asyncio.get_event_loop().run_until_complete(run_test())
    assert result is True


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_split_brain_middleware_allows_without_detector(
    simple_app: FastAPI,
) -> None:
    """Test that middleware allows requests when no detector is configured."""
    from litefs_fastapi.middleware import SplitBrainMiddleware

    simple_app.add_middleware(SplitBrainMiddleware, detector=None)
    client = TestClient(simple_app)

    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# =============================================================================
# WriteForwardingMiddleware Tests
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_passes_reads_locally(
    simple_app: FastAPI,
    fake_replica_detector: FakePrimaryDetector,
) -> None:
    """Test that GET/HEAD/OPTIONS requests are handled locally on replicas."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware

    # Create a fake forwarding port that tracks calls
    class FakeForwardingPort:
        def __init__(self):
            self.forward_called = False

        def forward_request(self, *args, **kwargs):
            self.forward_called = True
            raise RuntimeError("Should not be called for reads")

    fake_forwarding = FakeForwardingPort()

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_replica_detector,
        forwarding_port=fake_forwarding,
        primary_url="http://primary:8000",
    )
    client = TestClient(simple_app)

    response = client.get("/read")
    assert response.status_code == 200
    assert response.json() == {"action": "read"}
    assert fake_forwarding.forward_called is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_handles_writes_locally_on_primary(
    simple_app: FastAPI,
    fake_primary_detector: FakePrimaryDetector,
) -> None:
    """Test that write requests are handled locally when node is primary."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware

    # Create a fake forwarding port that tracks calls
    class FakeForwardingPort:
        def __init__(self):
            self.forward_called = False

        def forward_request(self, *args, **kwargs):
            self.forward_called = True
            raise RuntimeError("Should not be called on primary")

    fake_forwarding = FakeForwardingPort()

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_primary_detector,
        forwarding_port=fake_forwarding,
        primary_url="http://primary:8000",
    )
    client = TestClient(simple_app)

    response = client.post("/write")
    assert response.status_code == 200
    assert response.json() == {"action": "write"}
    assert fake_forwarding.forward_called is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_forwards_writes_on_replica(
    simple_app: FastAPI,
    fake_replica_detector: FakePrimaryDetector,
) -> None:
    """Test that write requests are forwarded when node is replica."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware
    from litefs.adapters.ports import ForwardingResult

    # Create a fake forwarding port that returns a successful response
    class FakeForwardingPort:
        def __init__(self):
            self.forward_called = False
            self.last_method = None
            self.last_path = None

        def forward_request(
            self,
            primary_url: str,
            method: str,
            path: str,
            headers: dict,
            body: bytes | None = None,
            query_string: str = "",
        ) -> ForwardingResult:
            self.forward_called = True
            self.last_method = method
            self.last_path = path
            return ForwardingResult(
                status_code=201,
                headers={"Content-Type": "application/json"},
                body=b'{"forwarded": true}',
            )

    fake_forwarding = FakeForwardingPort()

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_replica_detector,
        forwarding_port=fake_forwarding,
        primary_url="http://primary:8000",
    )
    client = TestClient(simple_app)

    response = client.post("/write")
    assert response.status_code == 201
    assert fake_forwarding.forward_called is True
    assert fake_forwarding.last_method == "POST"
    assert fake_forwarding.last_path == "/write"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_adds_headers(
    simple_app: FastAPI,
    fake_replica_detector: FakePrimaryDetector,
) -> None:
    """Test that forwarded responses include X-LiteFS-* headers."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware
    from litefs.adapters.ports import ForwardingResult

    class FakeForwardingPort:
        def forward_request(self, *args, **kwargs) -> ForwardingResult:
            return ForwardingResult(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=b'{"forwarded": true}',
            )

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_replica_detector,
        forwarding_port=FakeForwardingPort(),
        primary_url="http://primary:8000",
    )
    client = TestClient(simple_app)

    response = client.post("/write")
    assert "X-LiteFS-Forwarded" in response.headers
    assert response.headers["X-LiteFS-Forwarded"] == "true"
    assert "X-LiteFS-Primary-Node" in response.headers


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_excludes_paths(
    simple_app: FastAPI,
    fake_replica_detector: FakePrimaryDetector,
) -> None:
    """Test that excluded paths are not forwarded."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware

    class FakeForwardingPort:
        def __init__(self):
            self.forward_called = False

        def forward_request(self, *args, **kwargs):
            self.forward_called = True
            raise RuntimeError("Should not be called for excluded paths")

    fake_forwarding = FakeForwardingPort()

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_replica_detector,
        forwarding_port=fake_forwarding,
        primary_url="http://primary:8000",
        excluded_paths=("/write",),  # Exclude /write from forwarding
    )
    client = TestClient(simple_app)

    response = client.post("/write")
    assert response.status_code == 200
    assert response.json() == {"action": "write"}
    assert fake_forwarding.forward_called is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
def test_write_forwarding_disabled_when_no_forwarding_port(
    simple_app: FastAPI,
    fake_replica_detector: FakePrimaryDetector,
) -> None:
    """Test that forwarding is disabled when no forwarding_port is provided."""
    from litefs_fastapi.middleware import WriteForwardingMiddleware

    simple_app.add_middleware(
        WriteForwardingMiddleware,
        primary_detector=fake_replica_detector,
        forwarding_port=None,
        primary_url="http://primary:8000",
    )
    client = TestClient(simple_app)

    # Even on replica, should handle locally when forwarding is disabled
    response = client.post("/write")
    assert response.status_code == 200
    assert response.json() == {"action": "write"}
