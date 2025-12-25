"""Unit tests for health check view."""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest
from django.test import RequestFactory
from django.http import JsonResponse

from litefs.domain.health import HealthStatus
from litefs.usecases.failover_coordinator import NodeState
from litefs_django.views import health_check_view


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestHealthCheckView:
    """Test the health check endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def test_health_check_returns_json_response(self):
        """Test that health check endpoint returns JSON response."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    # Setup mocks
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        assert isinstance(response, JsonResponse)
        assert response.status_code == 200

    def test_health_check_returns_is_primary_true(self):
        """Test that health check returns is_primary=true when node is primary."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert data["is_primary"] is True

    def test_health_check_returns_is_primary_false(self):
        """Test that health check returns is_primary=false when node is replica."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = False
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.REPLICA
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert data["is_primary"] is False

    def test_health_check_includes_health_status(self):
        """Test that health check includes health status from HealthChecker."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert "health_status" in data
        assert data["health_status"] == "healthy"

    def test_health_check_includes_degraded_status(self):
        """Test that health check includes degraded health status."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="degraded")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert data["health_status"] == "degraded"

    def test_health_check_includes_unhealthy_status(self):
        """Test that health check includes unhealthy status."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="unhealthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert data["health_status"] == "unhealthy"

    def test_health_check_includes_cluster_info(self):
        """Test that health check includes cluster state information."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert "cluster" in data
        assert isinstance(data["cluster"], dict)

    def test_health_check_includes_node_state(self):
        """Test that health check includes node state from FailoverCoordinator."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        assert "cluster" in data
        assert "node_state" in data["cluster"]
        assert data["cluster"]["node_state"] in ("primary", "replica")

    def test_health_check_response_structure_complete(self):
        """Test that health check response has complete expected structure."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        data = json.loads(response.content)
        # Verify complete structure
        assert "is_primary" in data
        assert "health_status" in data
        assert "cluster" in data
        assert "node_state" in data["cluster"]

    def test_health_check_handles_litefs_not_running_returns_error(self):
        """Test that health check handles LiteFS not running error gracefully."""
        request = self.factory.get("/health/")

        from litefs.usecases.primary_detector import LiteFSNotRunningError

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.side_effect = LiteFSNotRunningError("Mount not found")
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="unhealthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.REPLICA
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

        assert response.status_code in (200, 503)
        data = json.loads(response.content)
        # Should handle error gracefully
        assert "health_status" in data or "error" in data

    def test_health_check_uses_health_checker_for_status(self):
        """Test that health check uses HealthChecker use case."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

                    # Verify check_health was called
                    mock_health.check_health.assert_called()

    def test_health_check_uses_primary_detector(self):
        """Test that health check uses PrimaryDetector."""
        request = self.factory.get("/health/")

        with patch("litefs_django.views.get_primary_detector") as mock_detector_func:
            with patch("litefs_django.views.get_health_checker") as mock_health_func:
                with patch("litefs_django.views.get_failover_coordinator") as mock_coord_func:
                    mock_detector = Mock()
                    mock_detector.is_primary.return_value = True
                    mock_detector_func.return_value = mock_detector

                    mock_health = Mock()
                    mock_health.check_health.return_value = HealthStatus(state="healthy")
                    mock_health_func.return_value = mock_health

                    mock_coord = Mock()
                    mock_coord.state = NodeState.PRIMARY
                    mock_coord_func.return_value = mock_coord

                    response = health_check_view(request)

                    # Verify is_primary was called
                    mock_detector.is_primary.assert_called()
