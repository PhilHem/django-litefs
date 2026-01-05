"""Unit tests for WriteForwardingMiddleware.

Tests cover HTTP method routing, header preservation, body forwarding,
and response passthrough per BDD specs in forwarding_core.feature.
"""

from __future__ import annotations

from unittest.mock import Mock
from typing import TYPE_CHECKING

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from litefs.adapters.ports import ForwardingResult, ForwardingPort
from litefs_django.middleware import WriteForwardingMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def request_factory() -> RequestFactory:
    """Django RequestFactory for creating test requests."""
    return RequestFactory()


@pytest.fixture
def mock_get_response() -> Mock:
    """Mock get_response callable that returns a simple 200 response."""
    response = HttpResponse("OK", status=200)
    return Mock(return_value=response)


@pytest.fixture
def mock_forwarding_port() -> Mock:
    """Mock ForwardingPort that returns a successful response."""
    port = Mock(spec=ForwardingPort)
    port.forward_request.return_value = ForwardingResult(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b'{"success": true}',
    )
    return port


@pytest.fixture
def mock_primary_detector() -> Mock:
    """Mock PrimaryDetector that reports node as replica."""
    detector = Mock()
    detector.is_primary.return_value = False
    return detector


@pytest.fixture
def mock_primary_detector_is_primary() -> Mock:
    """Mock PrimaryDetector that reports node as primary."""
    detector = Mock()
    detector.is_primary.return_value = True
    return detector


def create_middleware_with_mocks(
    get_response: Callable[[HttpRequest], HttpResponse],
    forwarding_port: ForwardingPort | None,
    primary_detector: Mock | None,
    primary_url: str = "http://primary.local:8000",
    excluded_paths: tuple[str, ...] = (),
) -> WriteForwardingMiddleware:
    """Create middleware with injected mocks for testing."""
    middleware = WriteForwardingMiddleware(get_response)
    middleware._forwarding_port = forwarding_port
    middleware._primary_detector = primary_detector
    middleware._primary_url = primary_url
    middleware._forwarding_enabled = forwarding_port is not None
    middleware._excluded_paths = excluded_paths
    return middleware


# ---------------------------------------------------------------------------
# HTTP Method Routing Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestWriteMethodsForwarded:
    """Write methods (POST, PUT, PATCH, DELETE) forwarded from replica to primary."""

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_write_methods_forwarded_from_replica(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
        method: str,
    ) -> None:
        """Write methods should be forwarded when on replica."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        # Create request with specified method
        request = getattr(request_factory, method.lower())("/api/resource")

        response = middleware(request)

        # Should have forwarded
        mock_forwarding_port.forward_request.assert_called_once()
        # get_response should NOT be called (request was forwarded)
        mock_get_response.assert_not_called()
        assert response.status_code == 200


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestReadMethodsNotForwarded:
    """Read methods (GET, HEAD, OPTIONS) handled locally on replica."""

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_read_methods_not_forwarded(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
        method: str,
    ) -> None:
        """Read methods should proceed to next middleware, no forwarding."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        if method == "OPTIONS":
            request = request_factory.options("/api/resource")
        else:
            request = getattr(request_factory, method.lower())("/api/resource")

        _response = middleware(request)  # noqa: F841

        # Should NOT forward
        mock_forwarding_port.forward_request.assert_not_called()
        # get_response SHOULD be called
        mock_get_response.assert_called_once_with(request)


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestPrimaryHandlesLocally:
    """Write requests handled locally on primary node."""

    def test_primary_handles_locally(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector_is_primary: Mock,
    ) -> None:
        """Primary node should not forward, handle locally."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector_is_primary,
        )

        request = request_factory.post("/api/resource")

        _response = middleware(request)  # noqa: F841

        # Should NOT forward (we are primary)
        mock_forwarding_port.forward_request.assert_not_called()
        # get_response SHOULD be called
        mock_get_response.assert_called_once_with(request)


# ---------------------------------------------------------------------------
# Request Header Preservation Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestHeaderPreservation:
    """Headers preserved during forwarding."""

    def test_headers_preserved(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Authorization, Content-Type, and custom headers should be preserved."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post(
            "/api/resource",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token123",
            HTTP_X_CUSTOM_HEADER="custom-value",
        )

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        headers = call_args.kwargs.get(
            "headers", call_args[0][3] if len(call_args[0]) > 3 else {}
        )

        assert "Authorization" in headers or "authorization" in headers.keys()
        assert "Content-Type" in headers or "content-type" in headers.keys()

    def test_host_header_rewritten(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Host header should be rewritten to primary."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
            primary_url="http://primary.local:8000",
        )

        request = request_factory.post(
            "/api/resource",
            HTTP_HOST="replica.local:8000",
        )

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        # Check primary_url was passed correctly (all keyword args)
        assert call_args.kwargs.get("primary_url") == "http://primary.local:8000"


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestXForwardedHeaders:
    """X-Forwarded-* headers added during forwarding."""

    def test_x_forwarded_headers_added(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """X-Forwarded-For, X-Forwarded-Host, X-Forwarded-Proto should be added."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_HOST"] = "replica.local:8000"

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        headers = call_args.kwargs.get(
            "headers", call_args[0][3] if len(call_args[0]) > 3 else {}
        )

        assert "X-Forwarded-For" in headers
        assert "192.168.1.100" in headers["X-Forwarded-For"]

    def test_x_forwarded_for_appended(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Existing X-Forwarded-For should be appended, not replaced."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post(
            "/api/resource",
            HTTP_X_FORWARDED_FOR="10.0.0.1",
        )
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        headers = call_args.kwargs.get(
            "headers", call_args[0][3] if len(call_args[0]) > 3 else {}
        )

        assert "X-Forwarded-For" in headers
        assert "10.0.0.1" in headers["X-Forwarded-For"]
        assert "192.168.1.100" in headers["X-Forwarded-For"]


# ---------------------------------------------------------------------------
# Request Body Preservation Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestBodyPreservation:
    """Request body preserved during forwarding."""

    def test_request_body_preserved(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """JSON body should be preserved identically."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        body = b'{"name": "test", "value": 123}'
        request = request_factory.post(
            "/api/resource",
            data=body,
            content_type="application/json",
        )

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        forwarded_body = call_args.kwargs.get(
            "body", call_args[0][4] if len(call_args[0]) > 4 else None
        )

        assert forwarded_body == body

    def test_query_string_preserved(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Query string should be preserved."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource?page=1&filter=active")

        middleware(request)

        call_args = mock_forwarding_port.forward_request.call_args
        query_string = call_args.kwargs.get(
            "query_string", call_args[0][5] if len(call_args[0]) > 5 else ""
        )

        assert "page=1" in query_string
        assert "filter=active" in query_string


# ---------------------------------------------------------------------------
# Response Passthrough Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestResponsePassthrough:
    """Response from primary passed through to client."""

    def test_response_status_passthrough(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Response status code should be passed through."""
        mock_forwarding_port.forward_request.return_value = ForwardingResult(
            status_code=201,
            headers={"Content-Type": "application/json"},
            body=b'{"id": 123}',
        )

        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response.status_code == 201

    def test_response_body_passthrough(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Response body should be passed through."""
        mock_forwarding_port.forward_request.return_value = ForwardingResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"id": 123}',
        )

        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response.content == b'{"id": 123}'

    def test_response_headers_passthrough(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Response headers should be passed through."""
        mock_forwarding_port.forward_request.return_value = ForwardingResult(
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "X-Custom-Header": "custom-value",
            },
            body=b"{}",
        )

        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response["X-Custom-Header"] == "custom-value"

    def test_error_response_passthrough(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Error response should be passed through."""
        mock_forwarding_port.forward_request.return_value = ForwardingResult(
            status_code=422,
            headers={"Content-Type": "application/json"},
            body=b'{"error": "validation failed"}',
        )

        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response.status_code == 422
        assert response.content == b'{"error": "validation failed"}'

    def test_redirect_response_passthrough(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Redirect response should be passed through."""
        mock_forwarding_port.forward_request.return_value = ForwardingResult(
            status_code=302,
            headers={"Location": "/api/resource/123"},
            body=b"",
        )

        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response.status_code == 302
        assert response["Location"] == "/api/resource/123"


# ---------------------------------------------------------------------------
# Forwarding Indicator Headers Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware")
class TestForwardingIndicatorHeaders:
    """Forwarding indicator headers in response."""

    def test_forwarded_response_includes_indicator(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Forwarded response should include X-LiteFS-Forwarded: true."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
            primary_url="http://primary.local:8000",
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert response["X-LiteFS-Forwarded"] == "true"

    def test_forwarded_response_includes_primary_node(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Forwarded response should include X-LiteFS-Primary-Node."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
            primary_url="http://primary.local:8000",
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert "X-LiteFS-Primary-Node" in response

    def test_local_response_excludes_indicator(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector_is_primary: Mock,
    ) -> None:
        """Local response should not include X-LiteFS-Forwarded."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector_is_primary,
        )

        request = request_factory.post("/api/resource")
        response = middleware(request)

        assert "X-LiteFS-Forwarded" not in response


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Http.WriteForwardingMiddleware.Config")
class TestForwardingConfiguration:
    """Forwarding enabled/disabled based on configuration."""

    def test_forwarding_disabled_when_not_configured(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """No forwarding when forwarding_port is None."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            forwarding_port=None,
            primary_detector=mock_primary_detector,
        )

        request = request_factory.post("/api/resource")
        _response = middleware(request)  # noqa: F841

        # get_response should be called (no forwarding)
        mock_get_response.assert_called_once_with(request)

    def test_excluded_paths_not_forwarded(
        self,
        request_factory: RequestFactory,
        mock_get_response: Mock,
        mock_forwarding_port: Mock,
        mock_primary_detector: Mock,
    ) -> None:
        """Excluded paths should not be forwarded."""
        middleware = create_middleware_with_mocks(
            mock_get_response,
            mock_forwarding_port,
            mock_primary_detector,
            excluded_paths=("/health", "/ready"),
        )

        request = request_factory.post("/health")
        _response = middleware(request)  # noqa: F841

        # Should NOT forward (excluded path)
        mock_forwarding_port.forward_request.assert_not_called()
        # get_response SHOULD be called
        mock_get_response.assert_called_once_with(request)
