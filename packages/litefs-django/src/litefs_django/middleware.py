"""Django middleware for split-brain detection and write forwarding.

This module provides two middleware classes:

1. SplitBrainMiddleware: Checks for split-brain conditions on each request and
   prevents access when multiple nodes claim leadership.

2. WriteForwardingMiddleware: Forwards write requests (POST, PUT, PATCH, DELETE)
   from replica nodes to the primary node.

Usage:
    Add to Django MIDDLEWARE in settings:

        MIDDLEWARE = [
            ...
            'litefs_django.middleware.SplitBrainMiddleware',
            'litefs_django.middleware.WriteForwardingMiddleware',
            ...
        ]

    SplitBrainMiddleware will:
    1. Check cluster state on each request
    2. Return 503 Service Unavailable if split-brain detected
    3. Send split_brain_detected signal for monitoring/logging
    4. Fail open (allow requests) if split-brain detection fails

    WriteForwardingMiddleware will:
    1. Detect if this node is a replica
    2. Forward write requests to the primary node
    3. Pass through responses from the primary
    4. Add X-LiteFS-Forwarded and X-LiteFS-Primary-Node headers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import HttpResponse, HttpRequest
from django.conf import settings as django_settings

from litefs.usecases.split_brain_detector import SplitBrainDetector
from litefs.usecases.path_exclusion_matcher import PathExclusionMatcher
from litefs.usecases.primary_url_resolver import PrimaryURLResolver
from litefs.adapters.ports import (
    SplitBrainDetectorPort,
    ForwardingPort,
    ForwardingResult,
    PrimaryDetectorPort,
)
from litefs_django.signals import split_brain_detected

if TYPE_CHECKING:
    from typing import Callable

logger = logging.getLogger(__name__)


class SplitBrainMiddleware:
    """Middleware to detect and prevent requests during split-brain scenarios.

    The middleware operates by:
    1. Checking cluster state via SplitBrainDetector on each request
    2. Returning 503 if multiple nodes claim leadership (split-brain)
    3. Sending split_brain_detected signal for applications to react
    4. Failing open (allowing requests) if detection fails

    Split-brain is a critical failure that must be detected early. The detector
    runs on every request to catch transitions to split-brain state.

    Thread safety:
        - Each request is handled independently
        - Detector is safe for concurrent calls (queries cluster state)
        - Signal sending is thread-safe in Django
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Initialize the split-brain detection middleware.

        Args:
            get_response: Django WSGI application callable
        """
        self.get_response = get_response
        self.detector: SplitBrainDetector | None = None

        # Try to initialize detector from settings on middleware load
        self._initialize_detector()

    def _initialize_detector(self) -> None:
        """Initialize SplitBrainDetector from Django settings.

        Attempts to create a SplitBrainDetector from LITEFS settings.
        If initialization fails, detector remains None and requests are allowed.
        """
        try:
            from litefs_django.settings import get_litefs_settings

            litefs_config = getattr(django_settings, "LITEFS", None)
            if not litefs_config:
                logger.debug(
                    "LITEFS settings not found. Split-brain detection disabled."
                )
                return

            if not litefs_config.get("ENABLED", True):
                logger.debug("LiteFS is disabled in settings. Detection disabled.")
                return

            # Get LiteFS settings domain object
            litefs_settings = get_litefs_settings(litefs_config)

            # Create detector based on leader election mode
            if litefs_settings.leader_election == "static":
                # Static mode: use PrimaryDetector (doesn't detect cluster state)
                logger.debug(
                    "Static leader election mode. Split-brain detection not applicable."
                )
                return

            # Raft mode: create detector with cluster state port
            # The port is obtained from LiteFS via the mount path
            from litefs.usecases.primary_detector import PrimaryDetector

            # Use PrimaryDetector's port for cluster state access
            detector_port = PrimaryDetector(litefs_settings.mount_path)

            # Verify port implements SplitBrainDetectorPort Protocol
            if not isinstance(detector_port, SplitBrainDetectorPort):
                logger.warning(
                    "PrimaryDetector does not implement SplitBrainDetectorPort. "
                    "Split-brain detection unavailable."
                )
                return

            # Create detector
            self.detector = SplitBrainDetector(detector_port)
            logger.debug("SplitBrainMiddleware initialized successfully.")

        except Exception as e:
            logger.warning(
                f"Failed to initialize SplitBrainMiddleware: {e}. "
                "Split-brain detection disabled. Requests will be allowed."
            )
            self.detector = None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request through split-brain detection.

        Checks for split-brain condition and returns 503 if detected.
        Otherwise passes request through to application.

        Args:
            request: Django HttpRequest object

        Returns:
            503 response if split-brain detected, otherwise application response
        """
        # If detector is not initialized, allow request
        if self.detector is None:
            return self.get_response(request)

        try:
            # Detect split-brain condition
            status = self.detector.detect_split_brain()

            # Send signal with detection result
            # Signal is sent for all detections (both split-brain and healthy)
            # Applications can filter in their receivers
            if status.is_split_brain:
                split_brain_detected.send(sender=self.__class__, status=status)
                logger.error(
                    f"Split-brain detected: {len(status.leader_nodes)} nodes claim leadership"
                )
                return self._create_split_brain_response()

        except Exception as e:
            # Fail open: if detection fails, allow request
            # Better to serve traffic than to block on detector failure
            logger.warning(
                f"Split-brain detection failed: {e}. Allowing request to proceed."
            )

        # No split-brain detected or detection failed - process request normally
        return self.get_response(request)

    @staticmethod
    def _create_split_brain_response() -> HttpResponse:
        """Create 503 Service Unavailable response for split-brain condition.

        Returns:
            HttpResponse with 503 status and split-brain message
        """
        response = HttpResponse(
            "Service Unavailable: Cluster split-brain detected. "
            "Multiple nodes claim leadership. Please check cluster state.",
            status=503,
            content_type="text/plain",
        )
        response["Retry-After"] = "30"  # Suggest retry after 30 seconds
        return response


# HTTP methods considered as writes that should be forwarded to primary
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class WriteForwardingMiddleware:
    """Middleware to forward write requests from replica to primary.

    This middleware intercepts write requests (POST, PUT, PATCH, DELETE) on
    replica nodes and forwards them to the primary node. Read requests
    (GET, HEAD, OPTIONS) are handled locally.

    The middleware adds the following headers to forwarded responses:
    - X-LiteFS-Forwarded: true
    - X-LiteFS-Primary-Node: <primary_url>

    Thread safety:
        - Each request is handled independently
        - No shared mutable state between requests
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Initialize the write forwarding middleware.

        Args:
            get_response: Django WSGI application callable
        """
        self.get_response = get_response

        # These are set during initialization or via test injection
        self._forwarding_port: ForwardingPort | None = None
        self._primary_detector: PrimaryDetectorPort | None = None
        self._primary_url: str | None = None
        self._forwarding_enabled: bool = False
        self._excluded_paths: tuple[str, ...] = ()
        self._path_matcher: PathExclusionMatcher | None = None
        self._url_resolver: PrimaryURLResolver | None = None

        # Try to initialize from settings
        self._initialize_forwarding()

    def _initialize_forwarding(self) -> None:
        """Initialize forwarding from Django settings.

        Attempts to configure forwarding from LITEFS settings.
        If initialization fails, forwarding remains disabled.
        """
        try:
            from litefs_django.settings import get_litefs_settings
            from litefs.adapters.httpx_forwarding import HTTPXForwardingAdapter

            litefs_config = getattr(django_settings, "LITEFS", None)
            if not litefs_config:
                logger.debug("LITEFS settings not found. Write forwarding disabled.")
                return

            if not litefs_config.get("ENABLED", True):
                logger.debug("LiteFS is disabled in settings. Forwarding disabled.")
                return

            # Get LiteFS settings domain object
            litefs_settings = get_litefs_settings(litefs_config)

            # Check if forwarding is configured and enabled
            if not litefs_settings.forwarding or not litefs_settings.forwarding.enabled:
                logger.debug("Write forwarding not enabled in settings.")
                return

            forwarding = litefs_settings.forwarding

            # Store for backwards compatibility
            self._primary_url = forwarding.primary_url
            self._excluded_paths = forwarding.excluded_paths
            self._forwarding_enabled = True

            # Create path exclusion matcher
            self._path_matcher = PathExclusionMatcher.from_forwarding_settings(
                forwarding
            )

            # Create primary detector
            from litefs.usecases.primary_detector import PrimaryDetector

            self._primary_detector = PrimaryDetector(litefs_settings.mount_path)

            # Create URL resolver (supports both static and Raft modes)
            self._url_resolver = PrimaryURLResolver(
                forwarding=forwarding,
                primary_url_detector=self._primary_detector,
                scheme=forwarding.scheme,
            )

            # Create forwarding adapter with timeout configuration
            self._forwarding_port = HTTPXForwardingAdapter.from_forwarding_settings(
                forwarding
            )

            logger.debug(
                f"WriteForwardingMiddleware initialized. "
                f"Primary URL: {self._primary_url}, "
                f"Connect timeout: {forwarding.connect_timeout}s, "
                f"Read timeout: {forwarding.read_timeout}s"
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize WriteForwardingMiddleware: {e}. "
                "Write forwarding disabled."
            )
            self._forwarding_enabled = False

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request through write forwarding logic.

        Forwards write requests to primary if this is a replica node.
        Read requests and requests on primary are handled locally.

        Args:
            request: Django HttpRequest object

        Returns:
            Response from primary (if forwarded) or local application response
        """
        # If forwarding is not enabled, pass through
        if not self._forwarding_enabled:
            return self.get_response(request)

        # If no forwarding port configured, pass through
        if self._forwarding_port is None:
            return self.get_response(request)

        # Check if this is a write method
        if request.method not in _WRITE_METHODS:
            return self.get_response(request)

        # Check if path is excluded
        if self._is_excluded_path(request.path):
            return self.get_response(request)

        # Check if this node is primary
        if self._is_primary():
            return self.get_response(request)

        # Forward write request to primary
        return self._forward_request(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path matches any exclusion pattern.

        Uses PathExclusionMatcher for glob and regex pattern matching.
        Falls back to simple string matching if matcher not initialized.

        Args:
            path: Request path to check

        Returns:
            True if path is excluded, False otherwise
        """
        if self._path_matcher is not None:
            return self._path_matcher.is_excluded(path)

        # Fallback for backwards compatibility or test injection
        return path in self._excluded_paths

    def _is_primary(self) -> bool:
        """Check if this node is the primary.

        Returns:
            True if this is the primary node, False if replica
        """
        if self._primary_detector is None:
            # If no detector, assume we should forward (safer default)
            return False

        try:
            return self._primary_detector.is_primary()
        except Exception as e:
            logger.warning(f"Failed to check primary status: {e}. Assuming replica.")
            return False

    def _forward_request(self, request: HttpRequest) -> HttpResponse:
        """Forward a write request to the primary node.

        Args:
            request: Django HttpRequest to forward

        Returns:
            HttpResponse from the primary node with forwarding headers added
        """
        if self._forwarding_port is None:
            logger.error("Cannot forward: forwarding port not configured")
            return self.get_response(request)

        # Resolve the primary URL using PrimaryURLResolver or fallback
        primary_url = self._resolve_primary_url()
        if primary_url is None:
            logger.error("Cannot forward: primary URL could not be resolved")
            return HttpResponse(
                "Service Unavailable: primary node unknown",
                status=503,
                content_type="text/plain",
            )

        # Build headers dict from Django request
        headers = self._extract_headers(request)

        # Add X-Forwarded-* headers
        self._add_forwarded_headers(request, headers)

        # Get request body
        body = request.body if request.body else None

        # Forward the request
        try:
            result = self._forwarding_port.forward_request(
                primary_url=primary_url,
                method=request.method,
                path=request.path,
                headers=headers,
                body=body,
                query_string=request.META.get("QUERY_STRING", ""),
            )
            return self._create_response(result, primary_url)
        except Exception as e:
            logger.error(f"Failed to forward request to primary: {e}")
            raise

    def _resolve_primary_url(self) -> str | None:
        """Resolve the primary node's full URL.

        Uses PrimaryURLResolver if available, otherwise falls back to
        the static _primary_url for backwards compatibility.

        Returns:
            Full URL with scheme or None if no primary available.
        """
        if self._url_resolver is not None:
            return self._url_resolver.resolve()

        # Fallback for backwards compatibility or test injection
        if self._primary_url:
            # Ensure URL has scheme
            if not self._primary_url.startswith(("http://", "https://")):
                return f"http://{self._primary_url}"
            return self._primary_url

        return None

    def _extract_headers(self, request: HttpRequest) -> dict[str, str]:
        """Extract HTTP headers from Django request.

        Converts Django META keys (HTTP_*) to standard header names.

        Args:
            request: Django HttpRequest

        Returns:
            Dict of header name to value
        """
        headers: dict[str, str] = {}

        for key, value in request.META.items():
            if key.startswith("HTTP_"):
                # Convert HTTP_HEADER_NAME to Header-Name
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key == "CONTENT_TYPE":
                headers["Content-Type"] = value
            elif key == "CONTENT_LENGTH":
                headers["Content-Length"] = value

        return headers

    def _add_forwarded_headers(
        self, request: HttpRequest, headers: dict[str, str]
    ) -> None:
        """Add X-Forwarded-* headers for proxy chain.

        Modifies headers dict in place.

        Args:
            request: Django HttpRequest
            headers: Headers dict to modify
        """
        # Get client IP
        client_ip = request.META.get("REMOTE_ADDR", "")

        # Handle X-Forwarded-For (append if exists)
        existing_xff = headers.get("X-Forwarded-For", "")
        if existing_xff:
            headers["X-Forwarded-For"] = f"{existing_xff}, {client_ip}"
        else:
            headers["X-Forwarded-For"] = client_ip

        # Add X-Forwarded-Host
        headers["X-Forwarded-Host"] = request.META.get("HTTP_HOST", "")

        # Add X-Forwarded-Proto
        scheme = "https" if request.is_secure() else "http"
        headers["X-Forwarded-Proto"] = scheme

    def _create_response(
        self, result: ForwardingResult, primary_url: str | None = None
    ) -> HttpResponse:
        """Create Django HttpResponse from ForwardingResult.

        Args:
            result: ForwardingResult from the primary node
            primary_url: The primary URL that was used for forwarding

        Returns:
            HttpResponse with primary's response data and forwarding headers
        """
        response = HttpResponse(
            content=result.body,
            status=result.status_code,
        )

        # Copy headers from primary response
        for header_name, header_value in result.headers.items():
            # Skip hop-by-hop headers that shouldn't be forwarded
            if header_name.lower() in ("connection", "keep-alive", "transfer-encoding"):
                continue
            response[header_name] = header_value

        # Add forwarding indicator headers
        response["X-LiteFS-Forwarded"] = "true"
        response["X-LiteFS-Primary-Node"] = primary_url or self._primary_url or ""

        return response
