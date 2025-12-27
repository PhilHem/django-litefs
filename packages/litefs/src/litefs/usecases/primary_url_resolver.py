"""Primary URL resolver use case for LiteFS.

Resolves the primary node's full URL from configuration, supporting both
static leader configuration and Raft-based dynamic discovery.
"""

from typing import Protocol

from litefs.domain.settings import ForwardingSettings


class PrimaryURLDetectorProtocol(Protocol):
    """Protocol for primary URL detection.

    Abstracts the mechanism for detecting the primary node URL,
    allowing injection of either the real PrimaryURLDetector or test fakes.
    """

    def get_primary_url(self) -> str | None:
        """Get the primary node URL.

        Returns:
            None: if no primary is elected
            "": if this node is primary (empty string)
            str: the primary URL/hostname if file has content
        """
        ...


class PrimaryURLResolver:
    """Resolves the primary node's full URL for write forwarding.

    This use case determines the primary URL based on configuration mode:

    1. Static leader mode: Uses the configured primary_url from ForwardingSettings
    2. Raft mode: Uses PrimaryURLDetector to read from LiteFS .primary file

    Static mode takes precedence when both are configured.

    Examples:
        Static mode::

            forwarding = ForwardingSettings(
                enabled=True,
                primary_url="primary.local:8080",
                scheme="http",
            )
            resolver = PrimaryURLResolver(forwarding=forwarding)
            url = resolver.resolve()  # "http://primary.local:8080"

        Raft mode::

            detector = PrimaryURLDetector(mount_path="/litefs")
            resolver = PrimaryURLResolver(
                forwarding=None,
                primary_url_detector=detector,
                scheme="http",
            )
            url = resolver.resolve()  # "http://raft-leader.local:20202" or None
    """

    def __init__(
        self,
        forwarding: ForwardingSettings | None = None,
        primary_url_detector: PrimaryURLDetectorProtocol | None = None,
        scheme: str = "http",
    ) -> None:
        """Initialize primary URL resolver.

        Args:
            forwarding: Optional ForwardingSettings for static leader mode.
                       When enabled with a primary_url, takes precedence.
            primary_url_detector: Optional detector for Raft-based mode.
                                 Used when static mode is unavailable.
            scheme: HTTP scheme to use (default: "http").
                   Used when primary_url_detector is provided.
                   ForwardingSettings has its own scheme field.
        """
        self._forwarding = forwarding
        self._detector = primary_url_detector
        self._scheme = scheme

    def resolve(self) -> str | None:
        """Resolve the primary node's full URL.

        Resolution order:
        1. Static mode: If forwarding is enabled with a primary_url, use it
        2. Raft mode: If detector is available, query it for primary URL
        3. Return None if no primary can be resolved

        Returns:
            Full URL with scheme (e.g., "http://primary.local:8080") or None
            if no primary is available.
        """
        # Try static mode first
        static_url = self._resolve_static()
        if static_url is not None:
            return static_url

        # Fall back to Raft mode
        return self._resolve_raft()

    def _resolve_static(self) -> str | None:
        """Resolve URL from static ForwardingSettings.

        Returns:
            Full URL with scheme or None if not configured/disabled.
        """
        if self._forwarding is None:
            return None

        if not self._forwarding.enabled:
            return None

        if self._forwarding.primary_url is None:
            return None

        scheme = self._forwarding.scheme
        return f"{scheme}://{self._forwarding.primary_url}"

    def _resolve_raft(self) -> str | None:
        """Resolve URL from Raft-based PrimaryURLDetector.

        Returns:
            Full URL with scheme or None if:
            - No detector configured
            - No primary elected (detector returns None)
            - This node is primary (detector returns empty string)
        """
        if self._detector is None:
            return None

        primary_url = self._detector.get_primary_url()

        # None means no primary elected
        if primary_url is None:
            return None

        # Empty string means this node is primary
        if primary_url == "":
            return None

        return f"{self._scheme}://{primary_url}"
