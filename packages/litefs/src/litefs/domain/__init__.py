"""Domain layer: Entities with zero external dependencies."""

from litefs.domain.settings import LiteFSSettings, StaticLeaderConfig
from litefs.domain.exceptions import LiteFSConfigError

__all__ = [
    "LiteFSSettings",
    "StaticLeaderConfig",
    "LiteFSConfigError",
]




