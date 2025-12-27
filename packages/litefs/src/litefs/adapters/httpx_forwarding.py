"""HTTPX-based implementation of the ForwardingPort.

This adapter uses httpx to forward HTTP requests from replicas to the primary node.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

from litefs.adapters.ports import ForwardingPort, ForwardingResult


class HTTPXForwardingAdapter:
    """HTTPX-based adapter for forwarding requests to primary node.

    Uses httpx to make HTTP requests to the primary, preserving headers,
    body, and query parameters while adding appropriate X-Forwarded-* headers.

    This adapter implements ForwardingPort for use by the forwarding middleware
    or use cases that need to redirect write requests to the primary.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the HTTPX forwarding adapter.

        Args:
            timeout: Request timeout in seconds. Defaults to 30.0.
            client: Optional httpx.Client for dependency injection (testing).
                   If not provided, a new client is created per request.
        """
        self._timeout = timeout
        self._client = client

    def forward_request(
        self,
        primary_url: str,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None = None,
        query_string: str = "",
    ) -> ForwardingResult:
        """Forward an HTTP request to the primary node.

        Preserves all headers except Host (rewritten to primary's host).
        Adds X-Forwarded-For, X-Forwarded-Host, and X-Forwarded-Proto headers.

        Args:
            primary_url: Base URL of the primary node (e.g., "http://primary:8080").
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: Request path (e.g., "/api/users").
            headers: Original request headers. Host will be rewritten.
            body: Optional request body bytes.
            query_string: Optional query string (without leading ?).

        Returns:
            ForwardingResult containing status code, headers, and body from primary.

        Raises:
            httpx.RequestError: For network failures or timeouts.
        """
        # Build target URL
        target_url = urljoin(primary_url.rstrip("/") + "/", path.lstrip("/"))
        if query_string:
            target_url = f"{target_url}?{query_string}"

        # Parse primary URL to get host
        parsed_primary = urlparse(primary_url)
        primary_host = parsed_primary.netloc

        # Get original host for X-Forwarded-Host
        original_host = headers.get("Host", headers.get("host", ""))

        # Get original client IP for X-Forwarded-For
        # Look for existing X-Forwarded-For or use the connection's remote addr
        existing_forwarded_for = headers.get(
            "X-Forwarded-For", headers.get("x-forwarded-for", "")
        )

        # Determine protocol for X-Forwarded-Proto
        # Check if original request was HTTPS
        original_proto = headers.get(
            "X-Forwarded-Proto", headers.get("x-forwarded-proto", "http")
        )

        # Build new headers
        new_headers: dict[str, str] = {}
        for key, value in headers.items():
            # Skip headers that we'll rewrite or that shouldn't be forwarded
            lower_key = key.lower()
            if lower_key in ("host", "content-length", "transfer-encoding"):
                continue
            new_headers[key] = value

        # Set Host to primary
        new_headers["Host"] = primary_host

        # Add X-Forwarded-* headers
        if original_host:
            new_headers["X-Forwarded-Host"] = original_host
        if existing_forwarded_for:
            new_headers["X-Forwarded-For"] = existing_forwarded_for
        new_headers["X-Forwarded-Proto"] = original_proto

        # Make the request
        if self._client is not None:
            response = self._client.request(
                method=method,
                url=target_url,
                headers=new_headers,
                content=body,
                timeout=self._timeout,
            )
        else:
            with httpx.Client() as client:
                response = client.request(
                    method=method,
                    url=target_url,
                    headers=new_headers,
                    content=body,
                    timeout=self._timeout,
                )

        # Convert response headers to dict
        response_headers = dict(response.headers)

        return ForwardingResult(
            status_code=response.status_code,
            headers=response_headers,
            body=response.content,
        )


# Runtime protocol check
assert isinstance(HTTPXForwardingAdapter(), ForwardingPort)
