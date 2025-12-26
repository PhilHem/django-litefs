"""Unit tests for Django health check views."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from django.http import HttpRequest
from django.test import RequestFactory

from litefs.domain.health import HealthStatus, LivenessResult, ReadinessResult
from litefs.usecases.liveness_checker import LivenessChecker
from litefs.usecases.readiness_checker import ReadinessChecker
from litefs_django.views import liveness_view, readiness_view

if TYPE_CHECKING:
    pass


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestLivenessView:
    """Test liveness_view Django endpoint."""

    @pytest.fixture
    def request_factory(self) -> RequestFactory:
        """Create Django request factory."""
        return RequestFactory()

    def test_liveness_view_returns_200_when_live(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that liveness_view returns 200 when node is live."""
        request = request_factory.get("/health/live")

        mock_checker = Mock(spec=LivenessChecker)
        mock_checker.check_liveness.return_value = LivenessResult(is_live=True)

        with patch(
            "litefs_django.views.get_liveness_checker", return_value=mock_checker
        ):
            response = liveness_view(request)

        assert response.status_code == 200

    def test_liveness_view_returns_503_when_not_live(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that liveness_view returns 503 when node is not live."""
        request = request_factory.get("/health/live")

        mock_checker = Mock(spec=LivenessChecker)
        mock_checker.check_liveness.return_value = LivenessResult(
            is_live=False, error="LiteFS not running"
        )

        with patch(
            "litefs_django.views.get_liveness_checker", return_value=mock_checker
        ):
            response = liveness_view(request)

        assert response.status_code == 503

    def test_liveness_view_returns_json_with_is_live_true(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that liveness_view returns JSON with is_live: true when live."""
        request = request_factory.get("/health/live")

        mock_checker = Mock(spec=LivenessChecker)
        mock_checker.check_liveness.return_value = LivenessResult(is_live=True)

        with patch(
            "litefs_django.views.get_liveness_checker", return_value=mock_checker
        ):
            response = liveness_view(request)

        data = json.loads(response.content)
        assert data == {"is_live": True}

    def test_liveness_view_returns_json_with_error_when_not_live(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that liveness_view returns JSON with is_live: false and error when not live."""
        request = request_factory.get("/health/live")

        mock_checker = Mock(spec=LivenessChecker)
        mock_checker.check_liveness.return_value = LivenessResult(
            is_live=False, error="LiteFS not running"
        )

        with patch(
            "litefs_django.views.get_liveness_checker", return_value=mock_checker
        ):
            response = liveness_view(request)

        data = json.loads(response.content)
        assert data == {"is_live": False, "error": "LiteFS not running"}

    def test_liveness_view_uses_get_method_only(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that liveness_view only accepts GET requests."""
        request = request_factory.post("/health/live")

        mock_checker = Mock(spec=LivenessChecker)
        mock_checker.check_liveness.return_value = LivenessResult(is_live=True)

        with patch(
            "litefs_django.views.get_liveness_checker", return_value=mock_checker
        ):
            response = liveness_view(request)

        # Should return 405 Method Not Allowed
        assert response.status_code == 405


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestReadinessView:
    """Test readiness_view Django endpoint."""

    @pytest.fixture
    def request_factory(self) -> RequestFactory:
        """Create Django request factory."""
        return RequestFactory()

    def test_readiness_view_returns_200_when_ready(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view returns 200 when node is ready."""
        request = request_factory.get("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=(),
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        assert response.status_code == 200

    def test_readiness_view_returns_503_when_not_ready(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view returns 503 when node is not ready."""
        request = request_factory.get("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="degraded"),
            split_brain_detected=False,
            leader_node_ids=(),
            error="Node is degraded",
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        assert response.status_code == 503

    def test_readiness_view_returns_json_with_all_fields(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view returns JSON with all required fields."""
        request = request_factory.get("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=(),
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        data = json.loads(response.content)
        assert data == {
            "is_ready": True,
            "can_accept_writes": True,
            "health_status": "healthy",
            "split_brain_detected": False,
        }

    def test_readiness_view_returns_json_with_error_when_not_ready(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view returns JSON with error when not ready."""
        request = request_factory.get("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=False,
            can_accept_writes=False,
            health_status=HealthStatus(state="unhealthy"),
            split_brain_detected=False,
            leader_node_ids=(),
            error="Node is unhealthy",
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        data = json.loads(response.content)
        assert data == {
            "is_ready": False,
            "can_accept_writes": False,
            "health_status": "unhealthy",
            "split_brain_detected": False,
            "error": "Node is unhealthy",
        }

    def test_readiness_view_includes_split_brain_info(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view includes split_brain_detected field."""
        request = request_factory.get("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=False,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=True,
            leader_node_ids=("node-1", "node-2"),
            error="Split brain detected: multiple leaders ('node-1', 'node-2')",
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        data = json.loads(response.content)
        assert data["split_brain_detected"] is True
        assert response.status_code == 503

    def test_readiness_view_uses_get_method_only(
        self, request_factory: RequestFactory
    ) -> None:
        """Test that readiness_view only accepts GET requests."""
        request = request_factory.post("/health/ready")

        mock_checker = Mock(spec=ReadinessChecker)
        mock_checker.check_readiness.return_value = ReadinessResult(
            is_ready=True,
            can_accept_writes=True,
            health_status=HealthStatus(state="healthy"),
            split_brain_detected=False,
            leader_node_ids=(),
        )

        with patch(
            "litefs_django.views.get_readiness_checker", return_value=mock_checker
        ):
            response = readiness_view(request)

        # Should return 405 Method Not Allowed
        assert response.status_code == 405
