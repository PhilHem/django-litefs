"""FastAPI ASGI middleware for split-brain detection and write forwarding.

This module provides two middleware classes:

1. SplitBrainMiddleware: Checks for split-brain conditions on each request and
   prevents access when multiple nodes claim leadership.

2. WriteForwardingMiddleware: Forwards write requests (POST, PUT, PATCH, DELETE)
   from replica nodes to the primary node.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send
    from litefs.adapters.ports import ForwardingPort, PrimaryDetectorPort
    from litefs.usecases.split_brain_detector import SplitBrainStatus

logger = logging.getLogger(__name__)

# HTTP methods considered as writes that should be forwarded to primary
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class SplitBrainDetectorProtocol(Protocol):
    """Protocol for split-brain detection."""

    def detect_split_brain(self) -> "SplitBrainStatus":
        """Detect split-brain condition."""
        ...


class SplitBrainMiddleware:
    """ASGI middleware to detect and prevent requests during split-brain scenarios.

    The middleware operates by:
    1. Checking cluster state via SplitBrainDetector on each HTTP request
    2. Returning 503 if multiple nodes claim leadership (split-brain)
    3. Failing open (allowing requests) if detection fails

    Split-brain is a critical failure that must be detected early. The detector
    runs on every request to catch transitions to split-brain state.

    Usage:
        from litefs_fastapi.middleware import SplitBrainMiddleware

        app.add_middleware(
            SplitBrainMiddleware,
            detector=split_brain_detector,
        )
    """

    def __init__(
        self,
        app: "ASGIApp",
        detector: SplitBrainDetectorProtocol | None = None,
    ) -> None:
        """Initialize the split-brain detection middleware.

        Args:
            app: ASGI application to wrap
            detector: SplitBrainDetector use case for checking cluster state.
                     If None, middleware passes all requests through.
        """
        self.app = app
        self.detector = detector

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """Process request through split-brain detection.

        For HTTP requests, checks for split-brain condition and returns 503 if detected.
        Non-HTTP scopes (websocket, lifespan) pass through without checking.

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only check HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # If no detector configured, pass through
        if self.detector is None:
            await self.app(scope, receive, send)
            return

        try:
            # Detect split-brain condition
            status = self.detector.detect_split_brain()

            if status.is_split_brain:
                logger.error(
                    f"Split-brain detected: {len(status.leader_nodes)} nodes claim leadership"
                )
                response = PlainTextResponse(
                    "Service Unavailable: Cluster split-brain detected. "
                    "Multiple nodes claim leadership. Please check cluster state.",
                    status_code=503,
                    headers={"Retry-After": "30"},
                )
                await response(scope, receive, send)
                return

        except Exception as e:
            # Fail open: if detection fails, allow request
            # Better to serve traffic than to block on detector failure
            logger.warning(
                f"Split-brain detection failed: {e}. Allowing request to proceed."
            )

        # No split-brain detected or detection failed - process request normally
        await self.app(scope, receive, send)


class WriteForwardingMiddleware:
    """ASGI middleware to forward write requests from replica to primary.

    This middleware intercepts write requests (POST, PUT, PATCH, DELETE) on
    replica nodes and forwards them to the primary node. Read requests
    (GET, HEAD, OPTIONS) are handled locally.

    The middleware adds the following headers to forwarded responses:
    - X-LiteFS-Forwarded: true
    - X-LiteFS-Primary-Node: <primary_url>

    Usage:
        from litefs_fastapi.middleware import WriteForwardingMiddleware
        from litefs.adapters.httpx_forwarding import HTTPXForwardingAdapter

        app.add_middleware(
            WriteForwardingMiddleware,
            primary_detector=primary_detector,
            forwarding_port=HTTPXForwardingAdapter(),
            primary_url="http://primary:8000",
        )
    """

    def __init__(
        self,
        app: "ASGIApp",
        primary_detector: "PrimaryDetectorPort",
        forwarding_port: "ForwardingPort | None" = None,
        primary_url: str = "",
        excluded_paths: tuple[str, ...] = (),
    ) -> None:
        """Initialize the write forwarding middleware.

        Args:
            app: ASGI application to wrap
            primary_detector: Port for checking if this node is primary
            forwarding_port: Port for forwarding requests to primary.
                           If None, forwarding is disabled.
            primary_url: URL of the primary node (e.g., "http://primary:8000")
            excluded_paths: Paths to exclude from forwarding (handled locally)
        """
        self.app = app
        self.primary_detector = primary_detector
        self.forwarding_port = forwarding_port
        self.primary_url = primary_url
        self.excluded_paths = excluded_paths

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """Process request through write forwarding logic.

        For HTTP requests:
        - Read methods (GET, HEAD, OPTIONS) are handled locally
        - Write methods on primary are handled locally
        - Write methods on replica are forwarded to primary (if configured)

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # If forwarding not configured, handle locally
        if self.forwarding_port is None:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")

        # Read methods are always handled locally
        if method not in _WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        # Check if path is excluded from forwarding
        if self._is_path_excluded(path):
            await self.app(scope, receive, send)
            return

        # Check if this node is primary
        try:
            is_primary = self.primary_detector.is_primary()
        except Exception as e:
            logger.warning(f"Failed to check primary status: {e}. Handling locally.")
            await self.app(scope, receive, send)
            return

        # Primary handles writes locally
        if is_primary:
            await self.app(scope, receive, send)
            return

        # Replica forwards writes to primary
        await self._forward_request(scope, receive, send)

    def _is_path_excluded(self, path: str) -> bool:
        """Check if path is excluded from forwarding.

        Args:
            path: Request path to check

        Returns:
            True if path matches any excluded pattern
        """
        for excluded in self.excluded_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return True
        return False

    async def _forward_request(
        self, scope: "Scope", receive: "Receive", send: "Send"
    ) -> None:
        """Forward the request to the primary node.

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable
            send: ASGI send callable
        """
        method = scope.get("method", "POST")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode("utf-8")

        # Extract headers from scope
        headers: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            headers[key.decode("utf-8")] = value.decode("utf-8")

        # Read request body
        body = await self._read_body(receive)

        try:
            # Forward the request
            result = self.forwarding_port.forward_request(  # type: ignore
                primary_url=self.primary_url,
                method=method,
                path=path,
                headers=headers,
                body=body,
                query_string=query_string,
            )

            # Build response with forwarding headers
            response_headers: dict[str, str] = dict(result.headers)
            response_headers["X-LiteFS-Forwarded"] = "true"
            response_headers["X-LiteFS-Primary-Node"] = self.primary_url

            response = Response(
                content=result.body,
                status_code=result.status_code,
                headers=response_headers,
            )
            await response(scope, receive, send)

        except Exception as e:
            logger.error(f"Failed to forward request: {e}")
            response = PlainTextResponse(
                f"Service Unavailable: Failed to forward request to primary: {e}",
                status_code=503,
                headers={"Retry-After": "5"},
            )
            await response(scope, receive, send)

    async def _read_body(self, receive: "Receive") -> bytes:
        """Read the full request body.

        Args:
            receive: ASGI receive callable

        Returns:
            Complete request body as bytes
        """
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        return body
