"""Django middleware for split-brain detection and handling.

This middleware checks for split-brain conditions on each request and prevents
access to the application when multiple nodes claim leadership.

Split-brain occurs when network partitions cause cluster consensus to break down,
resulting in multiple nodes believing they are the leader. This is a critical
failure mode that must be detected and handled before accepting requests.

Usage:
    Add to Django MIDDLEWARE in settings:

        MIDDLEWARE = [
            ...
            'litefs_django.middleware.SplitBrainMiddleware',
            ...
        ]

    The middleware will:
    1. Check cluster state on each request
    2. Return 503 Service Unavailable if split-brain detected
    3. Send split_brain_detected signal for monitoring/logging
    4. Fail open (allow requests) if split-brain detection fails
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.http import HttpResponse, HttpRequest
from django.conf import settings as django_settings

from litefs.usecases.split_brain_detector import SplitBrainDetector
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

            # Verify port has required method
            if not hasattr(detector_port, "get_cluster_state"):
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
                split_brain_detected.send(
                    sender=self.__class__, status=status
                )
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
