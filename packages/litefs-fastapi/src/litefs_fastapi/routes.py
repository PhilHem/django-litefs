"""FastAPI routes for LiteFS integration."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from litefs.usecases.health_checker import HealthChecker
from litefs.usecases.liveness_checker import LivenessChecker
from litefs.usecases.readiness_checker import ReadinessChecker
from litefs.usecases.split_brain_detector import SplitBrainDetector


def create_health_router(
    health_checker: HealthChecker,
    split_brain_detector: SplitBrainDetector,
    liveness_checker: LivenessChecker,
    readiness_checker: ReadinessChecker,
) -> APIRouter:
    """Create FastAPI router with health endpoints.

    Creates a router with three health-related endpoints:
    - /health: General health status with split-brain detection
    - /health/live: Kubernetes liveness probe (is LiteFS running?)
    - /health/ready: Kubernetes readiness probe (can accept traffic?)

    Args:
        health_checker: HealthChecker use case for node health status
        split_brain_detector: SplitBrainDetector use case for cluster split-brain detection
        liveness_checker: LivenessChecker use case for liveness probes
        readiness_checker: ReadinessChecker use case for readiness probes

    Returns:
        APIRouter configured with health endpoints
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

    @router.get("/health/live")
    def get_liveness() -> JSONResponse:
        """Liveness probe endpoint for Kubernetes/orchestrator health checks.

        Returns JSON indicating if the LiteFS process is running:
        - 200 OK: {'is_live': True} - LiteFS is running
        - 503 Service Unavailable: {'is_live': False, 'error': '...'} - LiteFS not running

        Returns:
            JSONResponse with liveness status
        """
        result = liveness_checker.check_liveness()

        if result.is_live:
            return JSONResponse(
                content={"is_live": True},
                status_code=200,
            )
        else:
            return JSONResponse(
                content={"is_live": False, "error": result.error},
                status_code=503,
            )

    @router.get("/health/ready")
    def get_readiness() -> JSONResponse:
        """Readiness probe endpoint for Kubernetes/orchestrator health checks.

        Returns JSON indicating if the node is ready to accept traffic:
        - 200 OK: Node is ready to accept traffic
        - 503 Service Unavailable: Node is not ready

        Response includes:
        - is_ready: Boolean indicating if node is ready
        - can_accept_writes: Boolean indicating if node can accept writes (is PRIMARY)
        - health_status: Health status (healthy/degraded/unhealthy)
        - split_brain_detected: Boolean indicating if split brain detected

        Returns:
            JSONResponse with readiness status
        """
        result = readiness_checker.check_readiness()

        response_data: dict[str, Any] = {
            "is_ready": result.is_ready,
            "can_accept_writes": result.can_accept_writes,
            "health_status": result.health_status.state,
            "split_brain_detected": result.split_brain_detected,
        }

        if result.error is not None:
            response_data["error"] = result.error

        status_code = 200 if result.is_ready else 503
        return JSONResponse(content=response_data, status_code=status_code)

    return router
