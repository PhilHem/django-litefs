"""Unit tests for CircuitBreaker domain entity."""

import pytest

from litefs.domain.circuit_breaker import CircuitBreaker, CircuitBreakerState
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.unit
class TestCircuitBreakerState:
    """Tests for CircuitBreakerState enum."""

    def test_has_closed_state(self) -> None:
        """CLOSED state exists."""
        assert CircuitBreakerState.CLOSED.value == "closed"

    def test_has_open_state(self) -> None:
        """OPEN state exists."""
        assert CircuitBreakerState.OPEN.value == "open"

    def test_has_half_open_state(self) -> None:
        """HALF_OPEN state exists."""
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"


@pytest.mark.unit
class TestCircuitBreakerValidation:
    """Tests for CircuitBreaker validation."""

    def test_threshold_must_be_positive(self) -> None:
        """Threshold must be at least 1."""
        with pytest.raises(LiteFSConfigError, match="threshold must be positive"):
            CircuitBreaker(threshold=0, reset_timeout=30.0)

    def test_threshold_negative_rejected(self) -> None:
        """Negative threshold is rejected."""
        with pytest.raises(LiteFSConfigError, match="threshold must be positive"):
            CircuitBreaker(threshold=-1, reset_timeout=30.0)

    def test_reset_timeout_must_be_positive(self) -> None:
        """Reset timeout must be positive."""
        with pytest.raises(LiteFSConfigError, match="reset_timeout must be positive"):
            CircuitBreaker(threshold=5, reset_timeout=0.0)

    def test_reset_timeout_negative_rejected(self) -> None:
        """Negative reset timeout is rejected."""
        with pytest.raises(LiteFSConfigError, match="reset_timeout must be positive"):
            CircuitBreaker(threshold=5, reset_timeout=-1.0)

    def test_valid_configuration_accepted(self) -> None:
        """Valid configuration creates circuit breaker."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.threshold == 5
        assert cb.reset_timeout == 30.0


@pytest.mark.unit
class TestCircuitBreakerDefaults:
    """Tests for CircuitBreaker default values."""

    def test_default_state_is_closed(self) -> None:
        """Default state is CLOSED."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_default_failure_count_is_zero(self) -> None:
        """Default failure count is zero."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.failure_count == 0

    def test_default_success_count_is_zero(self) -> None:
        """Default success count is zero."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.success_count == 0

    def test_default_opened_at_is_none(self) -> None:
        """Default opened_at is None."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.opened_at is None

    def test_default_disabled_is_false(self) -> None:
        """Default disabled is False."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.disabled is False


@pytest.mark.unit
class TestRecordFailure:
    """Tests for recording failures."""

    def test_increments_failure_count(self) -> None:
        """Recording failure increments failure count."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        updated = cb.record_failure(current_time=100.0)
        assert updated.failure_count == 1

    def test_returns_new_instance(self) -> None:
        """Recording failure returns new instance (immutable)."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        updated = cb.record_failure(current_time=100.0)
        assert updated is not cb
        assert cb.failure_count == 0  # Original unchanged

    def test_opens_circuit_at_threshold(self) -> None:
        """Circuit opens when failure count reaches threshold."""
        cb = CircuitBreaker(threshold=3, reset_timeout=30.0)
        cb = cb.record_failure(current_time=100.0)
        cb = cb.record_failure(current_time=101.0)
        assert cb.state == CircuitBreakerState.CLOSED
        cb = cb.record_failure(current_time=102.0)
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.opened_at == 102.0

    def test_resets_success_count_on_failure(self) -> None:
        """Success count resets on failure."""
        cb = CircuitBreaker(
            threshold=5, reset_timeout=30.0, success_count=2, failure_count=0
        )
        updated = cb.record_failure(current_time=100.0)
        assert updated.success_count == 0


@pytest.mark.unit
class TestRecordSuccess:
    """Tests for recording successes."""

    def test_resets_failure_count_in_closed_state(self) -> None:
        """Success in CLOSED state resets failure count."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0, failure_count=2)
        updated = cb.record_success()
        assert updated.failure_count == 0

    def test_increments_success_count_in_closed_state(self) -> None:
        """Success in CLOSED state increments success count."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        updated = cb.record_success()
        assert updated.success_count == 1

    def test_closes_circuit_from_half_open(self) -> None:
        """Success in HALF_OPEN state closes the circuit."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            failure_count=5,
            opened_at=100.0,
        )
        updated = cb.record_success()
        assert updated.state == CircuitBreakerState.CLOSED
        assert updated.failure_count == 0
        assert updated.opened_at is None

    def test_returns_new_instance(self) -> None:
        """Recording success returns new instance (immutable)."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        updated = cb.record_success()
        assert updated is not cb


@pytest.mark.unit
class TestShouldAllowRequest:
    """Tests for should_allow_request method."""

    def test_allows_when_closed(self) -> None:
        """Allows requests when circuit is CLOSED."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.should_allow_request(current_time=100.0) is True

    def test_blocks_when_open_before_timeout(self) -> None:
        """Blocks requests when OPEN and before timeout expires."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        assert cb.should_allow_request(current_time=110.0) is False

    def test_allows_when_open_after_timeout(self) -> None:
        """Allows probe request when OPEN and timeout expired."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        assert cb.should_allow_request(current_time=131.0) is True

    def test_allows_when_half_open(self) -> None:
        """Allows requests when circuit is HALF_OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            opened_at=100.0,
        )
        assert cb.should_allow_request(current_time=150.0) is True

    def test_allows_when_disabled(self) -> None:
        """Allows requests when disabled, even if OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            disabled=True,
        )
        assert cb.should_allow_request(current_time=101.0) is True


@pytest.mark.unit
class TestIsOpen:
    """Tests for is_open property."""

    def test_false_when_closed(self) -> None:
        """is_open is False when CLOSED."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.is_open is False

    def test_true_when_open(self) -> None:
        """is_open is True when OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        assert cb.is_open is True

    def test_false_when_half_open(self) -> None:
        """is_open is False when HALF_OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            opened_at=100.0,
        )
        assert cb.is_open is False


@pytest.mark.unit
class TestIsHalfOpen:
    """Tests for is_half_open method."""

    def test_false_when_closed(self) -> None:
        """is_half_open is False when CLOSED."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0)
        assert cb.is_half_open(current_time=100.0) is False

    def test_false_when_open_before_timeout(self) -> None:
        """is_half_open is False when OPEN before timeout."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        assert cb.is_half_open(current_time=110.0) is False

    def test_true_when_open_after_timeout(self) -> None:
        """is_half_open is True when OPEN after timeout."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        assert cb.is_half_open(current_time=131.0) is True

    def test_true_when_already_half_open(self) -> None:
        """is_half_open is True when already HALF_OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            opened_at=100.0,
        )
        assert cb.is_half_open(current_time=150.0) is True


@pytest.mark.unit
class TestFailedProbe:
    """Tests for failed probe (failure in HALF_OPEN state)."""

    def test_reopens_circuit(self) -> None:
        """Failed probe reopens the circuit."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            opened_at=100.0,
            failure_count=5,
        )
        updated = cb.record_failure(current_time=200.0)
        assert updated.state == CircuitBreakerState.OPEN
        assert updated.opened_at == 200.0

    def test_resets_failure_count_on_reopen(self) -> None:
        """Failure count resets to 1 on reopen from HALF_OPEN."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.HALF_OPEN,
            opened_at=100.0,
            failure_count=5,
        )
        updated = cb.record_failure(current_time=200.0)
        assert updated.failure_count == 1


@pytest.mark.unit
class TestDisabled:
    """Tests for disabled circuit breaker."""

    def test_disabled_allows_all_requests(self) -> None:
        """Disabled circuit allows all requests regardless of state."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
            disabled=True,
        )
        # Even though OPEN, disabled bypasses
        assert cb.should_allow_request(current_time=101.0) is True

    def test_disabled_still_records_failures(self) -> None:
        """Disabled circuit still records failures (for monitoring)."""
        cb = CircuitBreaker(threshold=5, reset_timeout=30.0, disabled=True)
        updated = cb.record_failure(current_time=100.0)
        assert updated.failure_count == 1

    def test_disabled_still_transitions_state(self) -> None:
        """Disabled circuit still transitions state (for monitoring)."""
        cb = CircuitBreaker(threshold=2, reset_timeout=30.0, disabled=True)
        cb = cb.record_failure(current_time=100.0)
        cb = cb.record_failure(current_time=101.0)
        assert cb.state == CircuitBreakerState.OPEN
        # But still allows requests
        assert cb.should_allow_request(current_time=102.0) is True


@pytest.mark.unit
class TestTransitionToHalfOpen:
    """Tests for explicit transition to HALF_OPEN state."""

    def test_transition_from_open_after_timeout(self) -> None:
        """Can transition from OPEN to HALF_OPEN after timeout."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        updated = cb.transition_to_half_open()
        assert updated.state == CircuitBreakerState.HALF_OPEN

    def test_transition_preserves_opened_at(self) -> None:
        """Transition to HALF_OPEN preserves opened_at for tracking."""
        cb = CircuitBreaker(
            threshold=5,
            reset_timeout=30.0,
            state=CircuitBreakerState.OPEN,
            opened_at=100.0,
        )
        updated = cb.transition_to_half_open()
        assert updated.opened_at == 100.0
