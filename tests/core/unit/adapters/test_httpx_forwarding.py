"""Unit tests for HTTPXForwardingAdapter."""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, Mock

import pytest

from litefs.adapters.ports import ForwardingPort, ForwardingResult
from litefs.adapters.httpx_forwarding import HTTPXForwardingAdapter


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Port.ForwardingPort")
class TestForwardingPort:
    """Test ForwardingPort protocol interface."""

    def test_protocol_has_forward_request_method(self) -> None:
        """Test that ForwardingPort has forward_request method."""
        assert hasattr(ForwardingPort, "forward_request")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that ForwardingPort is runtime_checkable."""

        class FakeForwarder:
            def forward_request(
                self,
                primary_url: str,
                method: str,
                path: str,
                headers: dict[str, str],
                body: bytes | None = None,
                query_string: str = "",
            ) -> ForwardingResult:
                return ForwardingResult(
                    status_code=200,
                    headers={},
                    body=b"",
                )

        fake = FakeForwarder()
        assert isinstance(fake, ForwardingPort)


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Contract.ForwardingResult")
class TestForwardingResult:
    """Test ForwardingResult dataclass."""

    def test_forwarding_result_is_frozen_dataclass(self) -> None:
        """Test that ForwardingResult is immutable (frozen)."""
        result = ForwardingResult(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"ok": true}',
        )

        with pytest.raises(FrozenInstanceError):
            result.status_code = 404  # type: ignore[misc]

    def test_forwarding_result_stores_status_code(self) -> None:
        """Test that ForwardingResult stores status code correctly."""
        result = ForwardingResult(status_code=201, headers={}, body=b"")
        assert result.status_code == 201

    def test_forwarding_result_stores_headers(self) -> None:
        """Test that ForwardingResult stores headers correctly."""
        headers = {"Content-Type": "text/plain", "X-Custom": "value"}
        result = ForwardingResult(status_code=200, headers=headers, body=b"")
        assert result.headers == headers

    def test_forwarding_result_stores_body(self) -> None:
        """Test that ForwardingResult stores body correctly."""
        body = b"Hello, World!"
        result = ForwardingResult(status_code=200, headers={}, body=body)
        assert result.body == body


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.HTTPXForwardingAdapter")
class TestHTTPXForwardingAdapter:
    """Test HTTPXForwardingAdapter implementation."""

    def test_satisfies_forwarding_port_protocol(self) -> None:
        """Test that HTTPXForwardingAdapter satisfies ForwardingPort protocol."""
        adapter = HTTPXForwardingAdapter()
        assert isinstance(adapter, ForwardingPort)

    def test_forward_request_preserves_method(self) -> None:
        """Test that forward_request uses correct HTTP method."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/users",
            headers={},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert call_kwargs.kwargs["method"] == "POST"

    def test_forward_request_preserves_path(self) -> None:
        """Test that forward_request preserves request path."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users/123",
            headers={},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert "/api/users/123" in call_kwargs.kwargs["url"]

    def test_forward_request_preserves_body(self) -> None:
        """Test that forward_request preserves request body."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        body = b'{"name": "test"}'
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/users",
            headers={},
            body=body,
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert call_kwargs.kwargs["content"] == body

    def test_forward_request_preserves_query_string(self) -> None:
        """Test that forward_request preserves query string."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={},
            query_string="page=1&limit=10",
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert "page=1&limit=10" in call_kwargs.kwargs["url"]

    def test_forward_request_rewrites_host_header(self) -> None:
        """Test that forward_request rewrites Host header to primary."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={"Host": "replica:8080"},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["Host"] == "primary:8080"

    def test_forward_request_adds_x_forwarded_host(self) -> None:
        """Test that forward_request adds X-Forwarded-Host header."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={"Host": "replica:8080"},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Forwarded-Host"] == "replica:8080"

    def test_forward_request_adds_x_forwarded_proto(self) -> None:
        """Test that forward_request adds X-Forwarded-Proto header."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "X-Forwarded-Proto" in headers

    def test_forward_request_preserves_existing_x_forwarded_for(self) -> None:
        """Test that forward_request preserves existing X-Forwarded-For."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={"X-Forwarded-For": "192.168.1.100"},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Forwarded-For"] == "192.168.1.100"

    def test_forward_request_returns_forwarding_result(self) -> None:
        """Test that forward_request returns ForwardingResult."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"id": 1}'
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        result = adapter.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/users",
            headers={},
            body=b'{"name": "test"}',
        )

        assert isinstance(result, ForwardingResult)
        assert result.status_code == 201
        assert result.headers == {"Content-Type": "application/json"}
        assert result.body == b'{"id": 1}'

    def test_forward_request_preserves_custom_headers(self) -> None:
        """Test that forward_request preserves custom headers."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={
                "Authorization": "Bearer token123",
                "X-Custom-Header": "custom-value",
            },
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Bearer token123"
        assert headers["X-Custom-Header"] == "custom-value"

    def test_forward_request_uses_configured_timeout(self) -> None:
        """Test that forward_request uses configured timeout."""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_client.request.return_value = mock_response

        adapter = HTTPXForwardingAdapter(timeout=60.0, client=mock_client)
        adapter.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/users",
            headers={},
        )

        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args
        assert call_kwargs.kwargs["timeout"] == 60.0
