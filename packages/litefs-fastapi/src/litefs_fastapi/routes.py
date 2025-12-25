"""FastAPI routes for LiteFS integration."""

from typing import Any

from fastapi import APIRouter

from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.split_brain_detector import SplitBrainDetector


def create_health_router(
    health_checker: HealthChecker, split_brain_detector: SplitBrainDetector
) -> APIRouter:
    """Create FastAPI router with health endpoint.

    The health endpoint returns the current health status of the node
    along with split-brain detection information. This enables monitoring
    systems to detect cluster state issues and take corrective action.

    Args:
        health_checker: HealthChecker use case instance for node health status
        split_brain_detector: SplitBrainDetector use case for cluster split-brain detection

    Returns:
        APIRouter configured with the /health endpoint
    """
    router = APIRouter()

    @router.get("/health")
    def get_health() -> dict[str, Any]:
        """Get health status of the LiteFS node.

        Returns JSON response including:
        - health_state: One of "healthy", "degraded", or "unhealthy"
        - is_split_brain: Boolean indicating if cluster split-brain is detected
        - leader_nodes: List of nodes claiming leadership in the cluster

        Returns:
            dict with keys: health_state, is_split_brain, leader_nodes
        """
        # Check health status
        health_status = health_checker.check_health()

        # Detect split-brain condition
        split_brain_status = split_brain_detector.detect_split_brain()

        # Build response
        response: dict[str, Any] = {
            "health_state": health_status.state,
            "is_split_brain": split_brain_status.is_split_brain,
            "leader_nodes": [
                {"node_id": node.node_id, "is_leader": node.is_leader}
                for node in split_brain_status.leader_nodes
            ],
        }

        return response

    return router
