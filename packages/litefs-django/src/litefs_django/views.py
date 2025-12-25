"""Health check view for LiteFS Django adapter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.failover_coordinator import FailoverCoordinator
from litefs.adapters.ports import PrimaryDetectorPort
from litefs_django.settings import get_litefs_settings

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


def get_failover_coordinator() -> FailoverCoordinator:
    """Get or create FailoverCoordinator instance.

    Returns:
        FailoverCoordinator for accessing node state.

    Raises:
        RuntimeError: If leader election is not configured.
    """
    from django.conf import settings as django_settings
    from litefs.adapters.ports import EnvironmentNodeIDResolver
    from litefs.usecases.leader_election import RaftLeaderElection
    from litefs.usecases.primary_initializer import PrimaryInitializer

    litefs_config = getattr(django_settings, "LITEFS", None)
    if not litefs_config:
        raise RuntimeError("LITEFS settings not configured")

    litefs_settings = get_litefs_settings(litefs_config)

    # Determine election mode and create appropriate leader election port
    if litefs_settings.leader_election == "static":
        if litefs_settings.static_leader_config is None:
            raise RuntimeError("Static leader election configured but no config found")

        resolver = EnvironmentNodeIDResolver()
        current_node_id = resolver.resolve_node_id()
        initializer = PrimaryInitializer(litefs_settings.static_leader_config)

        # Create a simple leader election port for static mode
        class StaticLeaderElection:
            """Static leader election implementation."""

            def __init__(self, initializer: PrimaryInitializer, node_id: str) -> None:
                self.initializer = initializer
                self.node_id = node_id

            def is_leader_elected(self) -> bool:
                return self.initializer.is_primary(self.node_id)

            def elect_as_leader(self) -> None:
                pass

            def demote_from_leader(self) -> None:
                pass

        election = StaticLeaderElection(initializer, current_node_id)
    else:
        # Raft mode
        election = RaftLeaderElection(
            mount_path=litefs_settings.mount_path,
            raft_addr=litefs_settings.raft_self_addr or "",
        )

    return FailoverCoordinator(election)


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
