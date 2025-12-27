"""Unit tests for RetryPolicy domain value object."""

import pytest

from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.retry import RetryPolicy


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RetryPolicy")
class TestRetryPolicy:
    """Test RetryPolicy value object."""

    def test_create_with_defaults(self) -> None:
        """Test creating RetryPolicy with default values."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.backoff_base == 1.0
        assert policy.max_backoff == 30.0

    def test_create_with_custom_values(self) -> None:
        """Test creating RetryPolicy with custom values."""
        policy = RetryPolicy(max_retries=5, backoff_base=2.0, max_backoff=60.0)
        assert policy.max_retries == 5
        assert policy.backoff_base == 2.0
        assert policy.max_backoff == 60.0

    def test_frozen_dataclass_immutable(self) -> None:
        """Test that RetryPolicy is immutable (frozen dataclass)."""
        policy = RetryPolicy()
        with pytest.raises(AttributeError):
            policy.max_retries = 10  # type: ignore

    def test_validation_max_retries_negative_raises(self) -> None:
        """Test that negative max_retries raises LiteFSConfigError."""
        with pytest.raises(LiteFSConfigError, match="max_retries cannot be negative"):
            RetryPolicy(max_retries=-1)

    def test_validation_max_retries_zero_allowed(self) -> None:
        """Test that zero max_retries is allowed (no retries)."""
        policy = RetryPolicy(max_retries=0)
        assert policy.max_retries == 0

    def test_validation_backoff_base_negative_raises(self) -> None:
        """Test that negative backoff_base raises LiteFSConfigError."""
        with pytest.raises(LiteFSConfigError, match="backoff_base must be positive"):
            RetryPolicy(backoff_base=-1.0)

    def test_validation_backoff_base_zero_raises(self) -> None:
        """Test that zero backoff_base raises LiteFSConfigError."""
        with pytest.raises(LiteFSConfigError, match="backoff_base must be positive"):
            RetryPolicy(backoff_base=0.0)

    def test_validation_max_backoff_negative_raises(self) -> None:
        """Test that negative max_backoff raises LiteFSConfigError."""
        with pytest.raises(LiteFSConfigError, match="max_backoff must be positive"):
            RetryPolicy(max_backoff=-1.0)

    def test_validation_max_backoff_zero_raises(self) -> None:
        """Test that zero max_backoff raises LiteFSConfigError."""
        with pytest.raises(LiteFSConfigError, match="max_backoff must be positive"):
            RetryPolicy(max_backoff=0.0)

    def test_calculate_backoff_delay_exponential(self) -> None:
        """Test exponential backoff calculation."""
        policy = RetryPolicy(backoff_base=1.0, max_backoff=30.0)
        # Attempt 0: 1.0 * 2^0 = 1.0
        assert policy.calculate_backoff(attempt=0) == 1.0
        # Attempt 1: 1.0 * 2^1 = 2.0
        assert policy.calculate_backoff(attempt=1) == 2.0
        # Attempt 2: 1.0 * 2^2 = 4.0
        assert policy.calculate_backoff(attempt=2) == 4.0
        # Attempt 3: 1.0 * 2^3 = 8.0
        assert policy.calculate_backoff(attempt=3) == 8.0

    def test_calculate_backoff_respects_max(self) -> None:
        """Test that backoff is capped at max_backoff."""
        policy = RetryPolicy(backoff_base=10.0, max_backoff=30.0)
        # Attempt 0: 10.0 * 2^0 = 10.0
        assert policy.calculate_backoff(attempt=0) == 10.0
        # Attempt 1: 10.0 * 2^1 = 20.0
        assert policy.calculate_backoff(attempt=1) == 20.0
        # Attempt 2: 10.0 * 2^2 = 40.0 -> capped at 30.0
        assert policy.calculate_backoff(attempt=2) == 30.0
        # Attempt 10: would be huge -> capped at 30.0
        assert policy.calculate_backoff(attempt=10) == 30.0

    def test_calculate_backoff_with_custom_base(self) -> None:
        """Test backoff calculation with custom base."""
        policy = RetryPolicy(backoff_base=0.5, max_backoff=30.0)
        # Attempt 0: 0.5 * 2^0 = 0.5
        assert policy.calculate_backoff(attempt=0) == 0.5
        # Attempt 1: 0.5 * 2^1 = 1.0
        assert policy.calculate_backoff(attempt=1) == 1.0

    def test_is_transient_error_connection_errors(self) -> None:
        """Test that connection errors are classified as transient."""
        policy = RetryPolicy()
        # Connection refused
        assert policy.is_transient_error(ConnectionRefusedError()) is True
        # Connection reset
        assert policy.is_transient_error(ConnectionResetError()) is True
        # Generic connection error
        assert policy.is_transient_error(ConnectionError()) is True

    def test_is_transient_error_timeout_errors(self) -> None:
        """Test that timeout errors are classified as transient."""
        policy = RetryPolicy()
        assert policy.is_transient_error(TimeoutError()) is True

    def test_is_transient_error_oserror_with_retryable_errno(self) -> None:
        """Test that specific OSError errnos are classified as transient."""
        policy = RetryPolicy()
        # ECONNREFUSED (111 on Linux)
        err = OSError(111, "Connection refused")
        assert policy.is_transient_error(err) is True
        # ETIMEDOUT (110 on Linux)
        err = OSError(110, "Connection timed out")
        assert policy.is_transient_error(err) is True
        # ECONNRESET (104 on Linux)
        err = OSError(104, "Connection reset by peer")
        assert policy.is_transient_error(err) is True

    def test_is_transient_error_permanent_errors(self) -> None:
        """Test that non-retryable errors are classified as permanent."""
        policy = RetryPolicy()
        # Value errors are not transient
        assert policy.is_transient_error(ValueError("bad value")) is False
        # Type errors are not transient
        assert policy.is_transient_error(TypeError("bad type")) is False
        # Attribute errors are not transient
        assert policy.is_transient_error(AttributeError("no attr")) is False
        # Generic exceptions are not transient
        assert policy.is_transient_error(Exception("generic")) is False

    def test_is_transient_error_oserror_non_retryable_errno(self) -> None:
        """Test that non-retryable OSError errnos are permanent."""
        policy = RetryPolicy()
        # ENOENT (2) - file not found
        err = OSError(2, "No such file or directory")
        assert policy.is_transient_error(err) is False
        # EACCES (13) - permission denied
        err = OSError(13, "Permission denied")
        assert policy.is_transient_error(err) is False

    def test_equality(self) -> None:
        """Test that policies with same values are equal."""
        policy1 = RetryPolicy(max_retries=3, backoff_base=1.0)
        policy2 = RetryPolicy(max_retries=3, backoff_base=1.0)
        assert policy1 == policy2

    def test_inequality(self) -> None:
        """Test that policies with different values are not equal."""
        policy1 = RetryPolicy(max_retries=3)
        policy2 = RetryPolicy(max_retries=5)
        assert policy1 != policy2

    def test_hashable(self) -> None:
        """Test that RetryPolicy is hashable."""
        policy = RetryPolicy()
        h = hash(policy)
        assert isinstance(h, int)

    def test_hash_consistency(self) -> None:
        """Test that equal policies have equal hashes."""
        policy1 = RetryPolicy(max_retries=3, backoff_base=1.0)
        policy2 = RetryPolicy(max_retries=3, backoff_base=1.0)
        assert hash(policy1) == hash(policy2)

    def test_should_retry_within_limit(self) -> None:
        """Test should_retry returns True within retry limit."""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(attempt=0) is True
        assert policy.should_retry(attempt=1) is True
        assert policy.should_retry(attempt=2) is True

    def test_should_retry_at_limit(self) -> None:
        """Test should_retry returns False at retry limit."""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(attempt=3) is False

    def test_should_retry_beyond_limit(self) -> None:
        """Test should_retry returns False beyond retry limit."""
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(attempt=4) is False
        assert policy.should_retry(attempt=100) is False

    def test_should_retry_zero_retries(self) -> None:
        """Test should_retry with zero max_retries (no retries allowed)."""
        policy = RetryPolicy(max_retries=0)
        assert policy.should_retry(attempt=0) is False
