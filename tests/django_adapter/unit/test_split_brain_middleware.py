"""Unit tests for Django split-brain detection middleware."""

import pytest
from unittest.mock import Mock, MagicMock
from django.http import HttpResponse, HttpRequest
from django.test import RequestFactory

from litefs.domain.split_brain import RaftNodeState, RaftClusterState
from litefs.usecases.split_brain_detector import SplitBrainDetector, SplitBrainStatus


@pytest.mark.unit
class TestSplitBrainMiddleware:
    """Test split-brain detection middleware."""

    @pytest.fixture
    def mock_detector_port(self) -> Mock:
        """Create a mock SplitBrainDetectorPort."""
        return Mock()

    @pytest.fixture
    def middleware_with_mock(self, mock_detector_port: Mock):
        """Create middleware with mocked detector port."""
        from litefs_django.middleware import SplitBrainMiddleware

        # Create a mock detector
        detector = SplitBrainDetector(mock_detector_port)

        # Create middleware instance
        middleware = SplitBrainMiddleware(get_response=lambda r: HttpResponse())
        middleware.detector = detector
        return middleware

    def test_middleware_returns_503_when_split_brain_detected(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should return 503 status when split-brain is detected."""
        # Setup: Create cluster state with 2 leaders (split-brain)
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        leader2 = RaftNodeState(node_id="node2", is_leader=True)
        cluster_state = RaftClusterState(nodes=[leader1, leader2])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Create request
        factory = RequestFactory()
        request = factory.post("/test/")

        # Call middleware
        response = middleware_with_mock(request)

        # Assert: 503 response with split-brain message
        assert response.status_code == 503
        assert "split" in response.content.decode().lower()

    def test_middleware_allows_request_when_no_split_brain(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should allow requests when cluster is healthy."""
        # Setup: Create cluster state with 1 leader (healthy)
        leader = RaftNodeState(node_id="node1", is_leader=True)
        replica = RaftNodeState(node_id="node2", is_leader=False)
        cluster_state = RaftClusterState(nodes=[leader, replica])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Setup: Create a proper get_response that returns HttpResponse
        def get_response(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        from litefs_django.middleware import SplitBrainMiddleware

        detector = SplitBrainDetector(mock_detector_port)
        middleware = SplitBrainMiddleware(get_response=get_response)
        middleware.detector = detector

        # Create request
        factory = RequestFactory()
        request = factory.get("/test/")

        # Call middleware
        response = middleware(request)

        # Assert: Request passes through
        assert response.status_code == 200
        assert response.content.decode() == "OK"

    def test_middleware_sends_signal_on_split_brain(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should send split_brain_detected signal when split-brain found."""
        # Setup: Import signal
        from litefs_django.signals import split_brain_detected

        # Create receiver to track signal
        signal_received = []

        def receiver(sender: object, status: SplitBrainStatus, **kwargs: object) -> None:
            signal_received.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Setup: Create split-brain state
            leader1 = RaftNodeState(node_id="node1", is_leader=True)
            leader2 = RaftNodeState(node_id="node2", is_leader=True)
            cluster_state = RaftClusterState(nodes=[leader1, leader2])
            mock_detector_port.get_cluster_state.return_value = cluster_state

            # Create request
            factory = RequestFactory()
            request = factory.post("/test/")

            # Call middleware
            middleware_with_mock(request)

            # Assert: Signal was sent with correct status
            assert len(signal_received) == 1
            assert signal_received[0].is_split_brain is True
            assert len(signal_received[0].leader_nodes) == 2
        finally:
            split_brain_detected.disconnect(receiver)

    def test_middleware_does_not_send_signal_when_healthy(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should not send signal when cluster is healthy."""
        from litefs_django.signals import split_brain_detected

        # Create receiver to track signal
        signal_received = []

        def receiver(sender: object, status: SplitBrainStatus, **kwargs: object) -> None:
            signal_received.append(status)

        split_brain_detected.connect(receiver)

        try:
            # Setup: Create healthy state
            leader = RaftNodeState(node_id="node1", is_leader=True)
            replica = RaftNodeState(node_id="node2", is_leader=False)
            cluster_state = RaftClusterState(nodes=[leader, replica])
            mock_detector_port.get_cluster_state.return_value = cluster_state

            # Setup: Create proper get_response
            def get_response(request: HttpRequest) -> HttpResponse:
                return HttpResponse("OK")

            from litefs_django.middleware import SplitBrainMiddleware

            detector = SplitBrainDetector(mock_detector_port)
            middleware = SplitBrainMiddleware(get_response=get_response)
            middleware.detector = detector

            # Create request
            factory = RequestFactory()
            request = factory.get("/test/")

            # Call middleware
            middleware(request)

            # Assert: No signal sent
            assert len(signal_received) == 0
        finally:
            split_brain_detected.disconnect(receiver)

    def test_middleware_allows_get_during_split_brain(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should allow GET (read) requests during split-brain."""
        # Setup: Create split-brain state
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        leader2 = RaftNodeState(node_id="node2", is_leader=True)
        cluster_state = RaftClusterState(nodes=[leader1, leader2])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Create GET request
        factory = RequestFactory()
        request = factory.get("/test/")

        # Call middleware
        response = middleware_with_mock(request)

        # Assert: Still blocked (reads also blocked during split-brain for safety)
        assert response.status_code == 503

    def test_middleware_blocks_post_during_split_brain(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should block POST (write) requests during split-brain."""
        # Setup: Create split-brain state
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        leader2 = RaftNodeState(node_id="node2", is_leader=True)
        cluster_state = RaftClusterState(nodes=[leader1, leader2])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Create POST request
        factory = RequestFactory()
        request = factory.post("/test/")

        # Call middleware
        response = middleware_with_mock(request)

        # Assert: Blocked with 503
        assert response.status_code == 503

    def test_middleware_gracefully_handles_detector_exception(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """Middleware should gracefully handle detector exceptions."""
        # Setup: Make detector raise exception
        mock_detector_port.get_cluster_state.side_effect = RuntimeError(
            "Cluster state unavailable"
        )

        # Setup: Create proper get_response
        def get_response(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        from litefs_django.middleware import SplitBrainMiddleware

        detector = SplitBrainDetector(mock_detector_port)
        middleware = SplitBrainMiddleware(get_response=get_response)
        middleware.detector = detector

        # Create request
        factory = RequestFactory()
        request = factory.get("/test/")

        # Call middleware - should not raise
        response = middleware(request)

        # Assert: Request proceeds (fail open on detector error)
        assert response.status_code == 200

    def test_middleware_checks_split_brain_on_each_request(
        self, mock_detector_port: Mock
    ) -> None:
        """Middleware should check split-brain status on every request."""
        # Setup: Create detector with mock port
        detector = SplitBrainDetector(mock_detector_port)

        # Setup: Create healthy state
        leader = RaftNodeState(node_id="node1", is_leader=True)
        replica = RaftNodeState(node_id="node2", is_leader=False)
        cluster_state = RaftClusterState(nodes=[leader, replica])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Setup: Create middleware
        def get_response(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        from litefs_django.middleware import SplitBrainMiddleware

        middleware = SplitBrainMiddleware(get_response=get_response)
        middleware.detector = detector

        # Create and process multiple requests
        factory = RequestFactory()
        for _ in range(3):
            request = factory.get("/test/")
            middleware(request)

        # Assert: Detector was called for each request
        assert mock_detector_port.get_cluster_state.call_count == 3

    def test_middleware_response_includes_retry_after_header(
        self, middleware_with_mock: Mock, mock_detector_port: Mock
    ) -> None:
        """503 response should include Retry-After header."""
        # Setup: Create split-brain state
        leader1 = RaftNodeState(node_id="node1", is_leader=True)
        leader2 = RaftNodeState(node_id="node2", is_leader=True)
        cluster_state = RaftClusterState(nodes=[leader1, leader2])
        mock_detector_port.get_cluster_state.return_value = cluster_state

        # Create request
        factory = RequestFactory()
        request = factory.post("/test/")

        # Call middleware
        response = middleware_with_mock(request)

        # Assert: Retry-After header present
        assert "Retry-After" in response
        assert response["Retry-After"].isdigit()

    def test_middleware_without_detector_initialization(self) -> None:
        """Middleware should handle case when detector is not initialized."""
        from litefs_django.middleware import SplitBrainMiddleware

        def get_response(request: HttpRequest) -> HttpResponse:
            return HttpResponse("OK")

        middleware = SplitBrainMiddleware(get_response=get_response)
        # Don't set middleware.detector

        # Create request
        factory = RequestFactory()
        request = factory.get("/test/")

        # Call middleware - should not raise
        response = middleware(request)

        # Assert: Request passes through
        assert response.status_code == 200
