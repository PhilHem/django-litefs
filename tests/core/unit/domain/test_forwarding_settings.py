"""Unit tests for ForwardingSettings domain value object."""

import pytest

from litefs.domain.settings import ForwardingSettings


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.ForwardingSettings")
class TestForwardingSettings:
    """Test ForwardingSettings value object."""

    def test_create_with_defaults(self) -> None:
        """Test creating config with default values."""
        fwd = ForwardingSettings()
        assert fwd.enabled is False
        assert fwd.primary_url is None
        assert fwd.timeout_seconds == 30.0
        assert fwd.retry_count == 1
        assert fwd.excluded_paths == ()
        assert fwd.scheme == "http"

    def test_create_with_all_fields(self) -> None:
        """Test creating config with all fields specified."""
        fwd = ForwardingSettings(
            enabled=True,
            primary_url="http://primary:8080",
            timeout_seconds=60.0,
            retry_count=3,
            excluded_paths=("/health", "/metrics"),
            scheme="https",
        )
        assert fwd.enabled is True
        assert fwd.primary_url == "http://primary:8080"
        assert fwd.timeout_seconds == 60.0
        assert fwd.retry_count == 3
        assert fwd.excluded_paths == ("/health", "/metrics")
        assert fwd.scheme == "https"

    def test_frozen_dataclass(self) -> None:
        """Test that ForwardingSettings is immutable."""
        fwd = ForwardingSettings()
        with pytest.raises(AttributeError):
            fwd.enabled = True  # type: ignore

    def test_excluded_paths_is_tuple(self) -> None:
        """Test that excluded_paths uses tuple for immutability."""
        fwd = ForwardingSettings(excluded_paths=("/api/write",))
        assert isinstance(fwd.excluded_paths, tuple)

    def test_equality(self) -> None:
        """Test that configs with same values are equal."""
        fwd1 = ForwardingSettings(enabled=True, timeout_seconds=30.0)
        fwd2 = ForwardingSettings(enabled=True, timeout_seconds=30.0)
        assert fwd1 == fwd2

    def test_inequality(self) -> None:
        """Test that configs with different values are not equal."""
        fwd1 = ForwardingSettings(enabled=True)
        fwd2 = ForwardingSettings(enabled=False)
        assert fwd1 != fwd2

    def test_hashable_due_to_tuple(self) -> None:
        """Test that ForwardingSettings is hashable due to tuple excluded_paths.

        Unlike ProxySettings which uses list (unhashable), ForwardingSettings
        uses tuple for excluded_paths, making it hashable.
        """
        fwd = ForwardingSettings(excluded_paths=("/health",))
        h = hash(fwd)
        assert isinstance(h, int)

    def test_timeout_configuration(self) -> None:
        """Test timeout configuration scenario."""
        fwd = ForwardingSettings(timeout_seconds=45.0)
        assert fwd.timeout_seconds == 45.0

    def test_path_exclusions(self) -> None:
        """Test path exclusions scenario with multiple paths."""
        excluded = ("/health", "/metrics", "/static/*")
        fwd = ForwardingSettings(excluded_paths=excluded)
        assert len(fwd.excluded_paths) == 3
        assert "/health" in fwd.excluded_paths
        assert "/metrics" in fwd.excluded_paths
        assert "/static/*" in fwd.excluded_paths

    def test_default_values_match_spec(self) -> None:
        """Test that default values match specification."""
        fwd = ForwardingSettings()
        # Spec: enabled (bool, default False)
        assert fwd.enabled is False
        # Spec: primary_url (str|None, default None)
        assert fwd.primary_url is None
        # Spec: timeout_seconds (float, default 30.0)
        assert fwd.timeout_seconds == 30.0
        # Spec: retry_count (int, default 1)
        assert fwd.retry_count == 1
        # Spec: excluded_paths (tuple[str, ...], default ())
        assert fwd.excluded_paths == ()
        # Spec: scheme (str, default "http")
        assert fwd.scheme == "http"

    def test_write_forwarding_enabled_scenario(self) -> None:
        """Test write forwarding configuration scenario."""
        fwd = ForwardingSettings(
            enabled=True,
            primary_url="http://primary-node:8080",
        )
        assert fwd.enabled is True
        assert fwd.primary_url == "http://primary-node:8080"

    def test_scheme_field_defaults_to_http(self) -> None:
        """Test that scheme field defaults to 'http'."""
        fwd = ForwardingSettings()
        assert fwd.scheme == "http"

    def test_scheme_field_can_be_set_to_https(self) -> None:
        """Test that scheme field can be set to 'https'."""
        fwd = ForwardingSettings(scheme="https")
        assert fwd.scheme == "https"

    def test_scheme_field_included_in_equality(self) -> None:
        """Test that scheme field is included in equality comparison."""
        fwd1 = ForwardingSettings(scheme="http")
        fwd2 = ForwardingSettings(scheme="https")
        assert fwd1 != fwd2

    def test_scheme_field_included_in_hash(self) -> None:
        """Test that scheme field is included in hash calculation."""
        fwd1 = ForwardingSettings(scheme="http")
        fwd2 = ForwardingSettings(scheme="https")
        assert hash(fwd1) != hash(fwd2)
