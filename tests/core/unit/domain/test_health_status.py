"""Unit tests for HealthStatus domain value object."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.health import HealthStatus
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.unit
class TestHealthStatus:
    """Test HealthStatus value object."""

    def test_create_healthy_status(self):
        """Test creating a healthy status."""
        status = HealthStatus(state="healthy")
        assert status.state == "healthy"

    def test_create_unhealthy_status(self):
        """Test creating an unhealthy status."""
        status = HealthStatus(state="unhealthy")
        assert status.state == "unhealthy"

    def test_create_degraded_status(self):
        """Test creating a degraded status."""
        status = HealthStatus(state="degraded")
        assert status.state == "degraded"

    def test_frozen_dataclass(self):
        """Test that HealthStatus is immutable."""
        status = HealthStatus(state="healthy")
        with pytest.raises(AttributeError):
            status.state = "unhealthy"  # type: ignore

    def test_equality_same_state(self):
        """Test that statuses with same state are equal."""
        status1 = HealthStatus(state="healthy")
        status2 = HealthStatus(state="healthy")
        assert status1 == status2

    def test_inequality_different_state(self):
        """Test that statuses with different states are not equal."""
        status1 = HealthStatus(state="healthy")
        status2 = HealthStatus(state="unhealthy")
        assert status1 != status2

    def test_hash_consistency(self):
        """Test that statuses with same state have same hash."""
        status1 = HealthStatus(state="healthy")
        status2 = HealthStatus(state="healthy")
        assert hash(status1) == hash(status2)

    def test_can_use_in_set(self):
        """Test that HealthStatus can be used in sets."""
        status1 = HealthStatus(state="healthy")
        status2 = HealthStatus(state="healthy")
        status3 = HealthStatus(state="unhealthy")

        status_set = {status1, status2, status3}
        assert len(status_set) == 2  # status1 and status2 are equal

    def test_can_use_as_dict_key(self):
        """Test that HealthStatus can be used as dictionary key."""
        status = HealthStatus(state="healthy")
        status_dict = {status: "primary_node"}

        # Can retrieve with identical status
        status_lookup = HealthStatus(state="healthy")
        assert status_dict[status_lookup] == "primary_node"

    def test_reject_invalid_state(self):
        """Test that invalid state is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be one of"):
            HealthStatus(state="invalid")  # type: ignore

    def test_reject_empty_state(self):
        """Test that empty state is rejected."""
        with pytest.raises(LiteFSConfigError, match="must be one of"):
            HealthStatus(state="")  # type: ignore

    def test_state_is_literal(self):
        """Test that state values are valid literals."""
        valid_states = ["healthy", "unhealthy", "degraded"]
        for state in valid_states:
            status = HealthStatus(state=state)  # type: ignore
            assert status.state == state


@pytest.mark.unit
@pytest.mark.property
class TestHealthStatusPBT:
    """Property-based tests for HealthStatus."""

    @given(
        state=st.sampled_from(["healthy", "unhealthy", "degraded"])
    )
    def test_valid_states_accepted(self, state):
        """PBT: Valid states should be accepted."""
        status = HealthStatus(state=state)  # type: ignore
        assert status.state == state

    @given(
        state=st.text().filter(
            lambda s: s not in ["healthy", "unhealthy", "degraded"]
        )
    )
    def test_invalid_states_rejected(self, state):
        """PBT: Invalid states should be rejected."""
        with pytest.raises(LiteFSConfigError):
            HealthStatus(state=state)  # type: ignore

    @given(
        state=st.sampled_from(["healthy", "unhealthy", "degraded"])
    )
    def test_idempotent_creation(self, state):
        """PBT: Creating status with same state should be idempotent."""
        status1 = HealthStatus(state=state)  # type: ignore
        status2 = HealthStatus(state=state)  # type: ignore

        assert status1 == status2
        assert hash(status1) == hash(status2)

    @given(
        state1=st.sampled_from(["healthy", "unhealthy", "degraded"]),
        state2=st.sampled_from(["healthy", "unhealthy", "degraded"]),
    )
    def test_equality_matches_state_equality(self, state1, state2):
        """PBT: Status equality should match state equality."""
        status1 = HealthStatus(state=state1)  # type: ignore
        status2 = HealthStatus(state=state2)  # type: ignore

        assert (status1 == status2) == (state1 == state2)
