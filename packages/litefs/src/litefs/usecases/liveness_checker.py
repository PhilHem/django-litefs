"""Liveness checker use case for determining if LiteFS is running."""

from litefs.adapters.ports import PrimaryDetectorPort
from litefs.domain.health import LivenessResult
from litefs.usecases.primary_detector import LiteFSNotRunningError


class LivenessChecker:
    """Checks if LiteFS is running (liveness probe).

    Use case that determines node liveness by attempting to check primary status.
    If LiteFS is running (regardless of primary/replica status), the node is live.
    If LiteFS is not running, the node is not live.

    This is a stateless, pure logic component with zero framework dependencies.
    It depends on PrimaryDetectorPort for checking if LiteFS is available.
    """

    def __init__(self, primary_detector: PrimaryDetectorPort) -> None:
        """Initialize the liveness checker.

        Args:
            primary_detector: Port implementation for checking if LiteFS is running.
        """
        self._primary_detector = primary_detector

    def check_liveness(self) -> LivenessResult:
        """Check if LiteFS is running.

        Attempts to call is_primary() on the detector. If the call succeeds
        (regardless of result), LiteFS is running and the node is live.
        If LiteFSNotRunningError is raised, LiteFS is not running.

        Returns:
            LivenessResult with is_live=True if LiteFS is running,
            is_live=False with error message if not running.
        """
        try:
            self._primary_detector.is_primary()
            return LivenessResult(is_live=True)
        except LiteFSNotRunningError as e:
            return LivenessResult(is_live=False, error=str(e))
