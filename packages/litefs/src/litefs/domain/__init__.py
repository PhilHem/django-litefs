"""Domain layer: Entities with zero external dependencies."""

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.health import HealthStatus

__all__ = [
    "LiteFSSettings",
    "StaticLeaderConfig",
    "LiteFSConfigError",
    "HealthStatus",
]




