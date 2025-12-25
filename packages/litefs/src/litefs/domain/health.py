"""Health status domain value object."""

from dataclasses import dataclass
from typing import Literal

from litefs.domain.exceptions import LiteFSConfigError


@dataclass(frozen=True)
class HealthStatus:
    """Health status value object.

    Represents the health state of a LiteFS node with three possible states:
    - healthy: Node is operating normally
    - degraded: Node is operating but with reduced capability
    - unhealthy: Node is not operational

    This is a domain value object with zero external dependencies.
    Instances are immutable and can be used as dictionary keys or in sets.

    Attributes:
        state: One of "healthy", "unhealthy", or "degraded".
    """

    state: Literal["healthy", "unhealthy", "degraded"]

    def __post_init__(self) -> None:
        """Validate health state after initialization."""
        self._validate_state()

    def _validate_state(self) -> None:
        """Validate that state is one of the allowed values."""
        valid_states = ("healthy", "unhealthy", "degraded")
        if self.state not in valid_states:
            raise LiteFSConfigError(
                f"health state must be one of {valid_states}, got: {self.state!r}"
            )
