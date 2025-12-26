"""Unit tests for LivenessChecker use case."""

import pytest

from litefs.domain.health import LivenessResult
from litefs.usecases.liveness_checker import LivenessChecker
from litefs.usecases.primary_detector import LiteFSNotRunningError


class FakePrimaryDetector:
    """In-memory fake for PrimaryDetector."""

    def __init__(self, *, is_primary: bool = True) -> None:
        self._is_primary = is_primary
        self._error: Exception | None = None

    def is_primary(self) -> bool:
        if self._error:
            raise self._error
        return self._is_primary

    def set_error(self, error: Exception | None) -> None:
        self._error = error


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.LivenessChecker")
class TestLivenessChecker:
    """Tests for LivenessChecker use case."""

    def test_check_liveness_returns_live_when_litefs_running(self) -> None:
        """When LiteFS is running, check_liveness returns is_live=True."""
        fake_detector = FakePrimaryDetector(is_primary=True)
        checker = LivenessChecker(primary_detector=fake_detector)

        result = checker.check_liveness()

        assert isinstance(result, LivenessResult)
        assert result.is_live is True
        assert result.error is None

    def test_check_liveness_returns_live_when_replica(self) -> None:
        """When LiteFS is running as replica, check_liveness still returns is_live=True."""
        fake_detector = FakePrimaryDetector(is_primary=False)
        checker = LivenessChecker(primary_detector=fake_detector)

        result = checker.check_liveness()

        assert result.is_live is True
        assert result.error is None

    def test_check_liveness_returns_not_live_when_litefs_not_running(self) -> None:
        """When LiteFS is not running, check_liveness returns is_live=False with error."""
        fake_detector = FakePrimaryDetector()
        fake_detector.set_error(LiteFSNotRunningError("Mount path missing"))
        checker = LivenessChecker(primary_detector=fake_detector)

        result = checker.check_liveness()

        assert result.is_live is False
        assert result.error == "Mount path missing"

    def test_check_liveness_captures_error_message(self) -> None:
        """Error message from exception is captured in result."""
        fake_detector = FakePrimaryDetector()
        fake_detector.set_error(
            LiteFSNotRunningError("LiteFS mount not found at /litefs")
        )
        checker = LivenessChecker(primary_detector=fake_detector)

        result = checker.check_liveness()

        assert result.is_live is False
        assert result.error == "LiteFS mount not found at /litefs"
