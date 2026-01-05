"""Unit tests for health domain value objects."""

import pytest

from litefs.domain.health import HealthStatus, LivenessResult, ReadinessResult


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.Health")
class TestLivenessResult:
    """Tests for LivenessResult value object."""

    def test_liveness_result_is_live_true(self) -> None:
        """LivenessResult with is_live=True indicates healthy node."""
        result = LivenessResult(is_live=True)
        assert result.is_live is True
        assert result.error is None

    def test_liveness_result_is_live_false_with_error(self) -> None:
        """LivenessResult with is_live=False can include error message."""
        result = LivenessResult(is_live=False, error="Connection timeout")
        assert result.is_live is False
        assert result.error == "Connection timeout"

    def test_liveness_result_default_error_is_none(self) -> None:
        """LivenessResult error defaults to None."""
        result = LivenessResult(is_live=False)
        assert result.error is None

    def test_liveness_result_is_frozen(self) -> None:
        """LivenessResult is immutable (frozen dataclass)."""
        result = LivenessResult(is_live=True)
        with pytest.raises(AttributeError):
            result.is_live = False  # type: ignore[misc]

    def test_liveness_result_equality(self) -> None:
        """LivenessResult instances with same values are equal."""
        result1 = LivenessResult(is_live=True, error=None)
        result2 = LivenessResult(is_live=True)
        assert result1 == result2

        result3 = LivenessResult(is_live=False, error="error")
        result4 = LivenessResult(is_live=False, error="error")
        assert result3 == result4

        assert result1 != result3


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.Health")
class TestHealthStatus:
    """Tests for HealthStatus value object (existing)."""

    def test_health_status_healthy(self) -> None:
        """HealthStatus accepts healthy state."""
        status = HealthStatus(state="healthy")
        assert status.state == "healthy"

    def test_health_status_unhealthy(self) -> None:
        """HealthStatus accepts unhealthy state."""
        status = HealthStatus(state="unhealthy")
        assert status.state == "unhealthy"

    def test_health_status_degraded(self) -> None:
        """HealthStatus accepts degraded state."""
        status = HealthStatus(state="degraded")
        assert status.state == "degraded"


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.Health")
class TestReadinessResult:
    """Tests for ReadinessResult value object."""

    def test_readiness_result_creation_ready(self) -> None:
        """ReadinessResult can be created with ready state."""
        result = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=("node-1",),
            error=None,
        )

        assert result.is_ready is True
        assert result.can_accept_writes is True
        assert result.health_status.state == "healthy"
        assert result.split_brain_detected is False
        assert result.leader_node_ids == ("node-1",)
        assert result.error is None

    def test_readiness_result_creation_not_ready(self) -> None:
        """ReadinessResult can be created with not ready state."""
        result = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="unhealthy"),
            split_brain_detected=False,
            leader_node_ids=(),
            error="Node not initialized",
        )

        assert result.is_ready is False
        assert result.can_accept_writes is False
        assert result.health_status.state == "unhealthy"
        assert result.leader_node_ids == ()
        assert result.error == "Node not initialized"

    def test_readiness_result_with_split_brain(self) -> None:
        """ReadinessResult correctly represents split-brain scenario."""
        result = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="degraded"),
            split_brain_detected=True,
            leader_node_ids=("node-1", "node-2"),
            error="Multiple leaders detected",
        )

        assert result.is_ready is False
        assert result.split_brain_detected is True
        assert result.leader_node_ids == ("node-1", "node-2")
        assert result.error == "Multiple leaders detected"

    def test_readiness_result_with_error(self) -> None:
        """ReadinessResult can store error message."""
        result = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="unhealthy"),
            split_brain_detected=False,
            leader_node_ids=(),
            error="Connection timeout",
        )

        assert result.error == "Connection timeout"

    def test_readiness_result_immutable(self) -> None:
        """ReadinessResult is immutable (frozen dataclass)."""
        result = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=("node-1",),
            error=None,
        )

        with pytest.raises(AttributeError):
            result.is_ready = False  # type: ignore[misc]

    def test_readiness_result_equality(self) -> None:
        """ReadinessResult instances with same values are equal."""
        result1 = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=("node-1",),
            error=None,
        )
        result2 = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=("node-1",),
            error=None,
        )

        assert result1 == result2

    def test_readiness_result_error_defaults_to_none(self) -> None:
        """ReadinessResult error field defaults to None."""
        result = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=("node-1",),
        )

        assert result.error is None
