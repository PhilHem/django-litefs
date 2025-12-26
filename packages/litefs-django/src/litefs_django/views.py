"""Health check view for LiteFS Django adapter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.failover_coordinator import FailoverCoordinator
from litefs.usecases.liveness_checker import LivenessChecker
from litefs.usecases.readiness_checker import ReadinessChecker
from litefs.adapters.ports import PrimaryDetectorPort, LeaderElectionPort
from litefs_django.settings import get_litefs_settings
from litefs_django.adapters import StaticLeaderElection

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


def get_primary_detector() -> PrimaryDetectorPort:
    """Get or create PrimaryDetector instance.

    Returns:
        PrimaryDetectorPort implementation for checking if node is primary.

    Raises:
        RuntimeError: If LITEFS settings are not available.
    """
    from django.conf import settings as django_settings

    litefs_config = getattr(django_settings, "LITEFS", None)
    if not litefs_config:
        raise RuntimeError("LITEFS settings not configured")

    litefs_settings = get_litefs_settings(litefs_config)
    return PrimaryDetector(litefs_settings.mount_path)


def get_health_checker() -> HealthChecker:
    """Get or create HealthChecker instance.

    Returns:
        HealthChecker use case for checking node health.

    Raises:
        RuntimeError: If LITEFS settings are not available.
    """
    primary_detector = get_primary_detector()
    return HealthChecker(primary_detector=primary_detector)


def get_liveness_checker() -> LivenessChecker:
    """Get or create LivenessChecker instance.

    Returns:
        LivenessChecker use case for checking if LiteFS is running.

    Raises:
        RuntimeError: If LITEFS settings are not available.
    """
    primary_detector = get_primary_detector()
    return LivenessChecker(primary_detector=primary_detector)


def get_failover_coordinator() -> FailoverCoordinator:
    """Get or create FailoverCoordinator instance.

    Returns:
        FailoverCoordinator for accessing node state.

    Raises:
        RuntimeError: If leader election is not configured.
    """
    from django.conf import settings as django_settings
    from litefs.adapters.ports import EnvironmentNodeIDResolver
    from litefs.factories import create_raft_leader_election
    from litefs.usecases.primary_initializer import PrimaryInitializer

    litefs_config = getattr(django_settings, "LITEFS", None)
    if not litefs_config:
        raise RuntimeError("LITEFS settings not configured")

    litefs_settings = get_litefs_settings(litefs_config)

    # Type annotation for the election variable
    election: LeaderElectionPort

    # Determine election mode and create appropriate leader election port
    if litefs_settings.leader_election == "static":
        if litefs_settings.static_leader_config is None:
            raise RuntimeError("Static leader election configured but no config found")

        resolver = EnvironmentNodeIDResolver()
        current_node_id = resolver.resolve_node_id()
        initializer = PrimaryInitializer(litefs_settings.static_leader_config)

        # Use the extracted StaticLeaderElection adapter
        election = StaticLeaderElection(initializer, current_node_id)
    else:
        # Raft mode - use factory
        resolver = EnvironmentNodeIDResolver()
        node_id = resolver.resolve_node_id()
        election = create_raft_leader_election(litefs_settings, node_id)

    return FailoverCoordinator(election)


def get_readiness_checker() -> ReadinessChecker:
    """Get or create ReadinessChecker instance.

    Returns:
        ReadinessChecker use case for checking node readiness.

    Raises:
        RuntimeError: If LITEFS settings are not available.
    """
    health_checker = get_health_checker()
    failover_coordinator = get_failover_coordinator()
    return ReadinessChecker(
        health_checker=health_checker,
        failover_coordinator=failover_coordinator,
    )


@require_http_methods(["GET"])
def health_check_view(request: HttpRequest) -> JsonResponse:
    """Health check endpoint returning leader status, cluster state, replication lag.

    Returns JSON with:
    - is_primary: Boolean indicating if this node is the primary
    - health_status: Health status from HealthChecker (healthy/degraded/unhealthy)
    - cluster: Cluster information including node state

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse with health check data
    """
    try:
        # Get all required services
        detector = get_primary_detector()
        health_checker = get_health_checker()
        coordinator = get_failover_coordinator()

        # Check primary status
        try:
            is_primary = detector.is_primary()
        except LiteFSNotRunningError:
            logger.warning("LiteFS not running, marking as unhealthy")
            is_primary = False

        # Check health status
        health_status = health_checker.check_health()

        # Get node state from coordinator
        node_state = coordinator.state.value  # NodeState enum value (primary/replica)

        # Build response
        response_data = {
            "is_primary": is_primary,
            "health_status": health_status.state,
            "cluster": {
                "node_state": node_state,
            },
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Return error response
        return JsonResponse(
            {
                "error": str(e),
                "health_status": "unhealthy",
                "is_primary": False,
            },
            status=503,
        )


@require_http_methods(["GET"])
def liveness_view(request: HttpRequest) -> JsonResponse:
    """Liveness probe endpoint for Kubernetes/orchestrator health checks.

    Returns JSON indicating if the LiteFS process is running:
    - 200 OK: {'is_live': True} - LiteFS is running
    - 503 Service Unavailable: {'is_live': False, 'error': '...'} - LiteFS not running

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse with liveness status
    """
    liveness_checker = get_liveness_checker()
    result = liveness_checker.check_liveness()

    if result.is_live:
        return JsonResponse({"is_live": True}, status=200)
    else:
        return JsonResponse(
            {"is_live": False, "error": result.error},
            status=503,
        )


@require_http_methods(["GET"])
def readiness_view(request: HttpRequest) -> JsonResponse:
    """Readiness probe endpoint for Kubernetes/orchestrator health checks.

    Returns JSON indicating if the node is ready to accept traffic:
    - 200 OK: Node is ready to accept traffic
    - 503 Service Unavailable: Node is not ready

    Response includes:
    - is_ready: Boolean indicating if node is ready
    - can_accept_writes: Boolean indicating if node can accept writes (is PRIMARY)
    - health_status: Health status (healthy/degraded/unhealthy)
    - split_brain_detected: Boolean indicating if split brain detected

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse with readiness status
    """
    readiness_checker = get_readiness_checker()
    result = readiness_checker.check_readiness()

    response_data: dict[str, object] = {
        "is_ready": result.is_ready,
        "can_accept_writes": result.can_accept_writes,
        "health_status": result.health_status.state,
        "split_brain_detected": result.split_brain_detected,
    }

    if result.error is not None:
        response_data["error"] = result.error

    status_code = 200 if result.is_ready else 503
    return JsonResponse(response_data, status=status_code)
