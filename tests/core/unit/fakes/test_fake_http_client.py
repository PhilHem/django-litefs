"""Tests for FakeHttpClient test double."""

from __future__ import annotations

import pytest

from litefs.adapters.ports import ForwardingPort, ForwardingResult

from .fake_http_client import FakeHttpClient


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientProtocol:
    """Verify FakeHttpClient implements ForwardingPort protocol."""

    def test_implements_forwarding_port_protocol(self) -> None:
        """FakeHttpClient must satisfy ForwardingPort protocol."""
        client = FakeHttpClient()
        assert isinstance(client, ForwardingPort)


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientDefaultBehavior:
    """Test default response behavior."""

    def test_default_response_status_code(self) -> None:
        """Default response has 200 status code."""
        client = FakeHttpClient()
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert result.status_code == 200

    def test_default_response_empty_headers(self) -> None:
        """Default response has empty headers dict."""
        client = FakeHttpClient()
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert result.headers == {}

    def test_default_response_empty_body(self) -> None:
        """Default response has empty body."""
        client = FakeHttpClient()
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert result.body == b""

    def test_returns_forwarding_result(self) -> None:
        """forward_request returns ForwardingResult instance."""
        client = FakeHttpClient()
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert isinstance(result, ForwardingResult)


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientConfigurableResponse:
    """Test configurable response behavior."""

    def test_custom_status_code(self) -> None:
        """Can set custom status code."""
        client = FakeHttpClient()
        client.set_response(status_code=404)
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/notfound",
            headers={},
        )
        assert result.status_code == 404

    def test_custom_headers(self) -> None:
        """Can set custom response headers."""
        client = FakeHttpClient()
        client.set_response(
            headers={"Content-Type": "application/json", "X-Custom": "value"}
        )
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert result.headers == {
            "Content-Type": "application/json",
            "X-Custom": "value",
        }

    def test_custom_body(self) -> None:
        """Can set custom response body."""
        client = FakeHttpClient()
        client.set_response(body=b'{"result": "success"}')
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/create",
            headers={},
        )
        assert result.body == b'{"result": "success"}'

    def test_combined_custom_response(self) -> None:
        """Can set all response attributes at once."""
        client = FakeHttpClient()
        client.set_response(
            status_code=201,
            headers={"Location": "/api/resource/1"},
            body=b'{"id": 1}',
        )
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/resource",
            headers={},
        )
        assert result.status_code == 201
        assert result.headers == {"Location": "/api/resource/1"}
        assert result.body == b'{"id": 1}'


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientExceptionBehavior:
    """Test exception raising behavior."""

    def test_raises_configured_exception(self) -> None:
        """Can configure client to raise exception."""
        client = FakeHttpClient()
        client.set_exception(ConnectionError("Network unreachable"))
        with pytest.raises(ConnectionError, match="Network unreachable"):
            client.forward_request(
                primary_url="http://primary:8080",
                method="GET",
                path="/api/test",
                headers={},
            )

    def test_raises_timeout_error(self) -> None:
        """Can configure client to raise timeout."""
        client = FakeHttpClient()
        client.set_exception(TimeoutError("Request timed out"))
        with pytest.raises(TimeoutError, match="Request timed out"):
            client.forward_request(
                primary_url="http://primary:8080",
                method="GET",
                path="/api/test",
                headers={},
            )

    def test_clear_exception(self) -> None:
        """Can clear exception to resume normal behavior."""
        client = FakeHttpClient()
        client.set_exception(ConnectionError("Failed"))
        client.set_exception(None)
        # Should not raise after clearing
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert result.status_code == 200


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientRequestRecording:
    """Test request recording for assertions."""

    def test_records_request_parameters(self) -> None:
        """Records all request parameters for later inspection."""
        client = FakeHttpClient()
        client.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/users",
            headers={"Authorization": "Bearer token"},
            body=b'{"name": "test"}',
            query_string="active=true",
        )
        assert len(client.requests) == 1
        req = client.requests[0]
        assert req["primary_url"] == "http://primary:8080"
        assert req["method"] == "POST"
        assert req["path"] == "/api/users"
        assert req["headers"] == {"Authorization": "Bearer token"}
        assert req["body"] == b'{"name": "test"}'
        assert req["query_string"] == "active=true"

    def test_multiple_requests_recorded(self) -> None:
        """Records multiple requests in order."""
        client = FakeHttpClient()
        client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/first",
            headers={},
        )
        client.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/second",
            headers={},
        )
        assert len(client.requests) == 2
        assert client.requests[0]["path"] == "/first"
        assert client.requests[1]["path"] == "/second"

    def test_clear_requests(self) -> None:
        """Can clear recorded requests."""
        client = FakeHttpClient()
        client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        client.clear_requests()
        assert len(client.requests) == 0

    def test_requests_recorded_even_with_exception(self) -> None:
        """Records request even when exception is raised."""
        client = FakeHttpClient()
        client.set_exception(ConnectionError("Failed"))
        with pytest.raises(ConnectionError):
            client.forward_request(
                primary_url="http://primary:8080",
                method="GET",
                path="/api/test",
                headers={},
            )
        assert len(client.requests) == 1
        assert client.requests[0]["path"] == "/api/test"


@pytest.mark.tier(1)
@pytest.mark.tra("Testing.Fake.HttpClient")
class TestFakeHttpClientOptionalParameters:
    """Test handling of optional parameters."""

    def test_body_defaults_to_none(self) -> None:
        """Body parameter defaults to None when not provided."""
        client = FakeHttpClient()
        client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert client.requests[0]["body"] is None

    def test_query_string_defaults_to_empty(self) -> None:
        """Query string defaults to empty string when not provided."""
        client = FakeHttpClient()
        client.forward_request(
            primary_url="http://primary:8080",
            method="GET",
            path="/api/test",
            headers={},
        )
        assert client.requests[0]["query_string"] == ""
