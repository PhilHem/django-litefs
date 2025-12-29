"""Binary resolver use case for coordinating platform detection and binary resolution."""

from litefs.adapters.ports import BinaryResolverPort, PlatformDetectorPort
from litefs.domain.binary import BinaryResolutionResult


class BinaryResolver:
    """Use case for resolving LiteFS binary location.

    Coordinates platform detection (via PlatformDetectorPort) and binary
    resolution (via BinaryResolverPort) to determine which LiteFS binary
    to use and where it's located.

    This use case orchestrates two ports to deliver the complete binary
    resolution workflow:
    1. Detect the current platform (OS and architecture)
    2. Resolve/find an existing binary on the filesystem
    3. Return a BinaryResolutionResult with platform and resolved path
    """

    def __init__(
        self,
        platform_detector: PlatformDetectorPort,
        binary_resolver: BinaryResolverPort,
    ) -> None:
        """Initialize the binary resolver use case.

        Args:
            platform_detector: Port for detecting current platform.
            binary_resolver: Port for resolving binary location on filesystem.
        """
        self._platform_detector = platform_detector
        self._binary_resolver = binary_resolver

    def __call__(self) -> BinaryResolutionResult:
        """Execute binary resolution workflow.

        Detects the current platform, then attempts to resolve an existing
        binary location on the filesystem.

        Returns:
            BinaryResolutionResult containing:
            - platform: The detected platform (os and arch)
            - resolved_path: Path to binary if found, None otherwise
        """
        # Step 1: Detect current platform
        platform = self._platform_detector.detect()

        # Step 2: Resolve binary location
        binary_location = self._binary_resolver.resolve()

        # Step 3: Build result
        resolved_path = binary_location.path if binary_location else None

        return BinaryResolutionResult(
            platform=platform,
            resolved_path=resolved_path,
        )
