"""Circuit breaker domain entity for write forwarding resilience."""

from dataclasses import dataclass, replace
from enum import Enum

from litefs.domain.exceptions import LiteFSConfigError


class CircuitBreakerState(Enum):
    """State of the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreaker:
    """Circuit breaker for write forwarding resilience.

    Implements the circuit breaker pattern to prevent cascading failures
    when forwarding writes to the primary node. The circuit breaker tracks
    consecutive failures and opens when a threshold is reached, preventing
    further requests until a timeout period has passed.

    State Machine:
        CLOSED -> OPEN: After `threshold` consecutive failures
        OPEN -> HALF_OPEN: After `reset_timeout` seconds
        HALF_OPEN -> CLOSED: On successful probe request
        HALF_OPEN -> OPEN: On failed probe request

    This is a frozen dataclass - all state transitions return new instances.

    Attributes:
        threshold: Number of consecutive failures before opening the circuit.
                  Must be positive.
        reset_timeout: Seconds to wait before allowing a probe request.
                      Must be positive.
        failure_count: Current consecutive failure count.
        success_count: Current consecutive success count.
        state: Current circuit breaker state.
        opened_at: Timestamp when the circuit was opened, or None if closed.
        disabled: If True, allows all requests regardless of state.
    """

    threshold: int
    reset_timeout: float
    failure_count: int = 0
    success_count: int = 0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    opened_at: float | None = None
    disabled: bool = False

    def __post_init__(self) -> None:
        """Validate circuit breaker configuration."""
        self._validate_threshold()
        self._validate_reset_timeout()

    def _validate_threshold(self) -> None:
        """Validate threshold is positive."""
        if self.threshold < 1:
            raise LiteFSConfigError("threshold must be positive")

    def _validate_reset_timeout(self) -> None:
        """Validate reset_timeout is positive."""
        if self.reset_timeout <= 0:
            raise LiteFSConfigError("reset_timeout must be positive")

    def record_failure(self, current_time: float) -> "CircuitBreaker":
        """Record a failed request and update state.

        Args:
            current_time: Current timestamp in seconds.

        Returns:
            New CircuitBreaker instance with updated state.
        """
        new_failure_count = self.failure_count + 1

        # In HALF_OPEN state, any failure reopens the circuit
        if self.state == CircuitBreakerState.HALF_OPEN:
            return replace(
                self,
                failure_count=1,  # Reset to 1 for new failure tracking
                success_count=0,
                state=CircuitBreakerState.OPEN,
                opened_at=current_time,
            )

        # Check if threshold reached
        if new_failure_count >= self.threshold:
            return replace(
                self,
                failure_count=new_failure_count,
                success_count=0,
                state=CircuitBreakerState.OPEN,
                opened_at=current_time,
            )

        # Just increment failure count
        return replace(
            self,
            failure_count=new_failure_count,
            success_count=0,
        )

    def record_success(self) -> "CircuitBreaker":
        """Record a successful request and update state.

        Returns:
            New CircuitBreaker instance with updated state.
        """
        # In HALF_OPEN state, success closes the circuit
        if self.state == CircuitBreakerState.HALF_OPEN:
            return replace(
                self,
                failure_count=0,
                success_count=1,
                state=CircuitBreakerState.CLOSED,
                opened_at=None,
            )

        # In CLOSED state, reset failure count and increment success
        return replace(
            self,
            failure_count=0,
            success_count=self.success_count + 1,
        )

    def should_allow_request(self, current_time: float) -> bool:
        """Determine if a request should be allowed through.

        Args:
            current_time: Current timestamp in seconds.

        Returns:
            True if the request should be allowed, False otherwise.
        """
        # Disabled bypasses all logic
        if self.disabled:
            return True

        # CLOSED always allows
        if self.state == CircuitBreakerState.CLOSED:
            return True

        # HALF_OPEN allows (for probe)
        if self.state == CircuitBreakerState.HALF_OPEN:
            return True

        # OPEN allows only after timeout (for probe)
        if self.state == CircuitBreakerState.OPEN and self.opened_at is not None:
            return current_time > self.opened_at + self.reset_timeout

        return False

    @property
    def is_open(self) -> bool:
        """Check if circuit is in OPEN state.

        Returns:
            True if state is OPEN, False otherwise.
        """
        return self.state == CircuitBreakerState.OPEN

    def is_half_open(self, current_time: float) -> bool:
        """Check if circuit is in or should be in HALF_OPEN state.

        Args:
            current_time: Current timestamp in seconds.

        Returns:
            True if state is HALF_OPEN or should transition to it.
        """
        if self.state == CircuitBreakerState.HALF_OPEN:
            return True

        # OPEN after timeout is effectively HALF_OPEN
        if self.state == CircuitBreakerState.OPEN and self.opened_at is not None:
            return current_time > self.opened_at + self.reset_timeout

        return False

    def transition_to_half_open(self) -> "CircuitBreaker":
        """Explicitly transition from OPEN to HALF_OPEN state.

        Returns:
            New CircuitBreaker instance in HALF_OPEN state.
        """
        return replace(
            self,
            state=CircuitBreakerState.HALF_OPEN,
        )
