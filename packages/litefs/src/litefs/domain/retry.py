"""Retry policy domain value object."""

from dataclasses import dataclass

from litefs.domain.exceptions import LiteFSConfigError

# Transient errno codes that indicate retryable network errors
# These are Linux errno values commonly seen in network operations
_TRANSIENT_ERRNOS = frozenset(
    {
        104,  # ECONNRESET - Connection reset by peer
        110,  # ETIMEDOUT - Connection timed out
        111,  # ECONNREFUSED - Connection refused
        113,  # EHOSTUNREACH - No route to host
        115,  # EINPROGRESS - Operation now in progress
    }
)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy configuration for forwarding resilience.

    Value object encapsulating retry configuration including max retries,
    exponential backoff calculation, and transient failure detection.

    This is a frozen dataclass with zero external dependencies, following
    Clean Architecture principles.

    Attributes:
        max_retries: Maximum number of retry attempts. 0 means no retries.
                    Must be non-negative.
        backoff_base: Base delay in seconds for exponential backoff.
                     Must be positive. Delay = backoff_base * 2^attempt.
        max_backoff: Maximum backoff delay in seconds. Backoff is capped
                    at this value to prevent excessive waits. Must be positive.
    """

    max_retries: int = 3
    backoff_base: float = 1.0
    max_backoff: float = 30.0

    def __post_init__(self) -> None:
        """Validate retry policy configuration."""
        self._validate_max_retries()
        self._validate_backoff_base()
        self._validate_max_backoff()

    def _validate_max_retries(self) -> None:
        """Validate max_retries is non-negative."""
        if self.max_retries < 0:
            raise LiteFSConfigError("max_retries cannot be negative")

    def _validate_backoff_base(self) -> None:
        """Validate backoff_base is positive."""
        if self.backoff_base <= 0:
            raise LiteFSConfigError("backoff_base must be positive")

    def _validate_max_backoff(self) -> None:
        """Validate max_backoff is positive."""
        if self.max_backoff <= 0:
            raise LiteFSConfigError("max_backoff must be positive")

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay for a given attempt.

        Uses exponential backoff: delay = backoff_base * 2^attempt,
        capped at max_backoff.

        Args:
            attempt: The retry attempt number (0-indexed).

        Returns:
            Delay in seconds before the next retry attempt.
        """
        delay = self.backoff_base * (2**attempt)
        return float(min(delay, self.max_backoff))

    def should_retry(self, attempt: int) -> bool:
        """Determine if another retry attempt should be made.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            True if attempt < max_retries, False otherwise.
        """
        return attempt < self.max_retries

    def is_transient_error(self, error: BaseException) -> bool:
        """Determine if an error is transient (retryable).

        Transient errors are temporary failures that may succeed on retry,
        such as connection errors, timeouts, and certain OS-level network
        errors.

        Args:
            error: The exception to classify.

        Returns:
            True if the error is transient and should be retried,
            False if it's a permanent error.
        """
        # Connection errors are transient
        if isinstance(error, ConnectionError):
            return True

        # Timeout errors are transient
        if isinstance(error, TimeoutError):
            return True

        # Check OSError with specific errno values
        if isinstance(error, OSError) and error.errno is not None:
            return error.errno in _TRANSIENT_ERRNOS

        # All other errors are considered permanent
        return False
