"""Fake HTTP client for testing request forwarding."""

from __future__ import annotations

from typing import TypedDict

from litefs.adapters.ports import ForwardingResult


class RecordedRequest(TypedDict):
    """Recorded request parameters for test assertions."""

    primary_url: str
    method: str
    path: str
    headers: dict[str, str]
    body: bytes | None
    query_string: str


class FakeHttpClient:
    """Fake HTTP client that returns configurable responses.

    Use this instead of mocking HTTP clients in unit tests for:
    - Faster test execution (no network I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (change responses during test)
    - Error injection (simulate network failures)
    - Request verification (inspect what was sent)

    Implements ForwardingPort protocol for use in BDD scenarios
    testing request forwarding to the primary node.

    Example:
        client = FakeHttpClient()
        client.set_response(status_code=201, body=b'{"id": 1}')
        result = client.forward_request(
            primary_url="http://primary:8080",
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            body=b'{"name": "test"}',
        )
        assert result.status_code == 201
        assert client.requests[0]["method"] == "POST"
    """

    def __init__(self) -> None:
        """Initialize with default 200 OK response."""
        self._status_code: int = 200
        self._headers: dict[str, str] = {}
        self._body: bytes = b""
        self._exception: BaseException | None = None
        self._requests: list[RecordedRequest] = []

    def forward_request(
        self,
        primary_url: str,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None = None,
        query_string: str = "",
    ) -> ForwardingResult:
        """Forward an HTTP request to the primary node (fake implementation).

        Records the request parameters and returns the configured response,
        or raises the configured exception.

        Args:
            primary_url: Base URL of the primary node.
            method: HTTP method.
            path: Request path.
            headers: Request headers.
            body: Optional request body.
            query_string: Optional query string.

        Returns:
            Configured ForwardingResult.

        Raises:
            The configured exception if set via set_exception().
        """
        self._requests.append(
            RecordedRequest(
                primary_url=primary_url,
                method=method,
                path=path,
                headers=headers,
                body=body,
                query_string=query_string,
            )
        )

        if self._exception is not None:
            raise self._exception

        return ForwardingResult(
            status_code=self._status_code,
            headers=self._headers.copy(),
            body=self._body,
        )

    def set_response(
        self,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> None:
        """Configure the response to return from forward_request().

        Args:
            status_code: HTTP status code to return. If None, keeps current value.
            headers: Response headers to return. If None, keeps current value.
            body: Response body to return. If None, keeps current value.
        """
        if status_code is not None:
            self._status_code = status_code
        if headers is not None:
            self._headers = headers
        if body is not None:
            self._body = body

    def set_exception(self, exception: BaseException | None) -> None:
        """Configure an exception to raise on next forward_request() call.

        Args:
            exception: Exception to raise, or None to clear and resume normal behavior.
        """
        self._exception = exception

    @property
    def requests(self) -> list[RecordedRequest]:
        """Get list of recorded requests for assertions.

        Returns:
            List of recorded request dictionaries in order of receipt.
        """
        return self._requests

    def clear_requests(self) -> None:
        """Clear all recorded requests."""
        self._requests.clear()
