"""Unit tests for HealthChecker use case."""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock

from litefs.usecases.health_checker import HealthChecker
from litefs.domain.health import HealthStatus
from litefs.adapters.ports import PrimaryDetectorPort


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestHealthChecker:
    """Test HealthChecker use case."""

    def test_check_health_primary_healthy(self):
        """Test that primary node with is_primary=True returns healthy."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(primary_detector=mock_detector)
        status = checker.check_health()

        assert status == HealthStatus(state="healthy")
        mock_detector.is_primary.assert_called_once()

    def test_check_health_replica_healthy(self):
        """Test that replica node with is_primary=False returns healthy."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = False

        checker = HealthChecker(primary_detector=mock_detector)
        status = checker.check_health()

        assert status == HealthStatus(state="healthy")
        mock_detector.is_primary.assert_called_once()

    def test_check_health_primary_degraded(self):
        """Test primary node with degraded=True returns degraded."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(primary_detector=mock_detector, degraded=True)
        status = checker.check_health()

        assert status == HealthStatus(state="degraded")

    def test_check_health_replica_degraded(self):
        """Test replica node with degraded=True returns degraded."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = False

        checker = HealthChecker(primary_detector=mock_detector, degraded=True)
        status = checker.check_health()

        assert status == HealthStatus(state="degraded")

    def test_check_health_primary_unhealthy(self):
        """Test primary node with unhealthy=True returns unhealthy."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(primary_detector=mock_detector, unhealthy=True)
        status = checker.check_health()

        assert status == HealthStatus(state="unhealthy")

    def test_check_health_replica_unhealthy(self):
        """Test replica node with unhealthy=True returns unhealthy."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = False

        checker = HealthChecker(primary_detector=mock_detector, unhealthy=True)
        status = checker.check_health()

        assert status == HealthStatus(state="unhealthy")

    def test_unhealthy_takes_precedence_over_degraded(self):
        """Test that unhealthy=True takes precedence over degraded=True."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(
            primary_detector=mock_detector,
            unhealthy=True,
            degraded=True
        )
        status = checker.check_health()

        assert status == HealthStatus(state="unhealthy")

    def test_degraded_takes_precedence_over_healthy(self):
        """Test that degraded=True takes precedence over healthy."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(
            primary_detector=mock_detector,
            degraded=True,
            unhealthy=False
        )
        status = checker.check_health()

        assert status == HealthStatus(state="degraded")

    def test_stateless_behavior(self):
        """Test that checker is stateless and doesn't maintain state between calls."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.side_effect = [True, False, True]

        checker = HealthChecker(primary_detector=mock_detector)

        # Call multiple times
        result1 = checker.check_health()
        result2 = checker.check_health()
        result3 = checker.check_health()

        # All should be healthy (detector returns True, False, True)
        assert result1 == HealthStatus(state="healthy")
        assert result2 == HealthStatus(state="healthy")
        assert result3 == HealthStatus(state="healthy")
        assert mock_detector.is_primary.call_count == 3

    def test_multiple_instances_independent(self):
        """Test that multiple checker instances are independent."""
        detector1: PrimaryDetectorPort = Mock()
        detector1.is_primary.return_value = True

        detector2: PrimaryDetectorPort = Mock()
        detector2.is_primary.return_value = False

        checker1 = HealthChecker(primary_detector=detector1)
        checker2 = HealthChecker(primary_detector=detector2, degraded=True)

        status1 = checker1.check_health()
        status2 = checker2.check_health()

        assert status1 == HealthStatus(state="healthy")
        assert status2 == HealthStatus(state="degraded")

    def test_check_health_always_calls_detector(self):
        """Test that check_health always calls the primary detector."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = True

        checker = HealthChecker(primary_detector=mock_detector)

        checker.check_health()
        checker.check_health()

        assert mock_detector.is_primary.call_count == 2

    def test_detector_port_interface(self):
        """Test that checker accepts any object implementing PrimaryDetectorPort."""
        # Create a simple object that implements the protocol
        class SimpleDetector:
            def is_primary(self) -> bool:
                return True

        detector = SimpleDetector()
        checker = HealthChecker(primary_detector=detector)
        status = checker.check_health()

        assert status == HealthStatus(state="healthy")


@pytest.mark.tier(3)
@pytest.mark.tra("UseCase")
class TestHealthCheckerPBT:
    """Property-based tests for HealthChecker."""

    @given(
        is_primary=st.booleans(),
        degraded=st.booleans(),
        unhealthy=st.booleans(),
    )
    def test_health_check_consistency(self, is_primary, degraded, unhealthy):
        """PBT: Health check result should be consistent with state flags."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = is_primary

        checker = HealthChecker(
            primary_detector=mock_detector,
            degraded=degraded,
            unhealthy=unhealthy
        )

        status = checker.check_health()

        # Determine expected state based on priority: unhealthy > degraded > healthy
        if unhealthy:
            expected_state = "unhealthy"
        elif degraded:
            expected_state = "degraded"
        else:
            expected_state = "healthy"

        assert status == HealthStatus(state=expected_state)  # type: ignore

    @given(
        is_primary=st.booleans()
    )
    def test_detector_result_independent_of_primary(self, is_primary):
        """PBT: Health status should not depend on is_primary value alone."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = is_primary

        checker1 = HealthChecker(primary_detector=mock_detector, degraded=False)
        checker2 = HealthChecker(primary_detector=mock_detector, degraded=True)

        status1 = checker1.check_health()
        status2 = checker2.check_health()

        # Degraded status should differ regardless of is_primary
        assert status1 != status2
        assert status1 == HealthStatus(state="healthy")  # type: ignore
        assert status2 == HealthStatus(state="degraded")  # type: ignore

    @given(
        is_primary=st.booleans()
    )
    def test_idempotent_health_checks(self, is_primary):
        """PBT: Multiple calls to check_health should return same result."""
        mock_detector: PrimaryDetectorPort = Mock()
        mock_detector.is_primary.return_value = is_primary

        checker = HealthChecker(primary_detector=mock_detector)

        result1 = checker.check_health()
        result2 = checker.check_health()
        result3 = checker.check_health()

        assert result1 == result2 == result3
        assert result1 == HealthStatus(state="healthy")  # type: ignore
