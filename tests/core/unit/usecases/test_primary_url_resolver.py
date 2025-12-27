"""Unit tests for PrimaryURLResolver use case."""

import pytest

from litefs.domain.settings import ForwardingSettings
from litefs.usecases.primary_url_resolver import PrimaryURLResolver


class FakePrimaryURLDetector:
    """Fake implementation for testing Raft-based URL detection."""

    def __init__(self, primary_url: str | None = None) -> None:
        """Initialize fake detector.

        Args:
            primary_url: URL to return from get_primary_url().
                        None means no primary, "" means this node is primary.
        """
        self._primary_url = primary_url

    def get_primary_url(self) -> str | None:
        """Return configured primary URL."""
        return self._primary_url


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLResolver")
class TestPrimaryURLResolverStaticMode:
    """Test PrimaryURLResolver with static leader configuration."""

    def test_returns_static_primary_url_when_forwarding_configured(self) -> None:
        """Test that configured primary_url from ForwardingSettings is returned."""
        forwarding = ForwardingSettings(
            enabled=True,
            primary_url="primary.local:8080",
            scheme="http",
        )
        resolver = PrimaryURLResolver(forwarding=forwarding)

        result = resolver.resolve()

        assert result == "http://primary.local:8080"

    def test_returns_https_url_when_scheme_is_https(self) -> None:
        """Test that https scheme is applied correctly."""
        forwarding = ForwardingSettings(
            enabled=True,
            primary_url="primary.local:8443",
            scheme="https",
        )
        resolver = PrimaryURLResolver(forwarding=forwarding)

        result = resolver.resolve()

        assert result == "https://primary.local:8443"

    def test_returns_none_when_forwarding_disabled(self) -> None:
        """Test that None is returned when forwarding is disabled."""
        forwarding = ForwardingSettings(
            enabled=False,
            primary_url="primary.local:8080",
        )
        resolver = PrimaryURLResolver(forwarding=forwarding)

        result = resolver.resolve()

        assert result is None

    def test_returns_none_when_no_primary_url_configured(self) -> None:
        """Test that None is returned when primary_url is not set."""
        forwarding = ForwardingSettings(
            enabled=True,
            primary_url=None,
        )
        resolver = PrimaryURLResolver(forwarding=forwarding)

        result = resolver.resolve()

        assert result is None

    def test_returns_none_when_forwarding_is_none(self) -> None:
        """Test that None is returned when no forwarding config provided."""
        resolver = PrimaryURLResolver(forwarding=None)

        result = resolver.resolve()

        assert result is None


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLResolver")
class TestPrimaryURLResolverRaftMode:
    """Test PrimaryURLResolver with Raft-based URL detection."""

    def test_returns_url_from_raft_detector(self) -> None:
        """Test that URL from Raft detector is returned with scheme."""
        fake_detector = FakePrimaryURLDetector(primary_url="raft-primary.local:20202")
        resolver = PrimaryURLResolver(
            forwarding=None,
            primary_url_detector=fake_detector,
            scheme="http",
        )

        result = resolver.resolve()

        assert result == "http://raft-primary.local:20202"

    def test_returns_none_when_no_primary_elected(self) -> None:
        """Test that None is returned when .primary file doesn't exist."""
        fake_detector = FakePrimaryURLDetector(primary_url=None)
        resolver = PrimaryURLResolver(
            forwarding=None,
            primary_url_detector=fake_detector,
        )

        result = resolver.resolve()

        assert result is None

    def test_returns_none_when_this_node_is_primary(self) -> None:
        """Test that None is returned when this node is primary (empty string)."""
        fake_detector = FakePrimaryURLDetector(primary_url="")
        resolver = PrimaryURLResolver(
            forwarding=None,
            primary_url_detector=fake_detector,
        )

        result = resolver.resolve()

        assert result is None

    def test_applies_https_scheme_to_raft_url(self) -> None:
        """Test that custom scheme is applied to Raft-detected URL."""
        fake_detector = FakePrimaryURLDetector(primary_url="raft-primary.local:20202")
        resolver = PrimaryURLResolver(
            forwarding=None,
            primary_url_detector=fake_detector,
            scheme="https",
        )

        result = resolver.resolve()

        assert result == "https://raft-primary.local:20202"


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PrimaryURLResolver")
class TestPrimaryURLResolverPrecedence:
    """Test resolution precedence between static and Raft modes."""

    def test_static_mode_takes_precedence_over_raft(self) -> None:
        """Test that forwarding config takes precedence over Raft detector."""
        forwarding = ForwardingSettings(
            enabled=True,
            primary_url="static-primary.local:8080",
            scheme="http",
        )
        fake_detector = FakePrimaryURLDetector(primary_url="raft-primary.local:20202")
        resolver = PrimaryURLResolver(
            forwarding=forwarding,
            primary_url_detector=fake_detector,
        )

        result = resolver.resolve()

        # Static config should win
        assert result == "http://static-primary.local:8080"

    def test_falls_back_to_raft_when_static_disabled(self) -> None:
        """Test fallback to Raft when forwarding is disabled."""
        forwarding = ForwardingSettings(
            enabled=False,
            primary_url="static-primary.local:8080",
        )
        fake_detector = FakePrimaryURLDetector(primary_url="raft-primary.local:20202")
        resolver = PrimaryURLResolver(
            forwarding=forwarding,
            primary_url_detector=fake_detector,
            scheme="http",
        )

        result = resolver.resolve()

        # Should fall back to Raft
        assert result == "http://raft-primary.local:20202"

    def test_falls_back_to_raft_when_static_url_missing(self) -> None:
        """Test fallback to Raft when forwarding enabled but no URL."""
        forwarding = ForwardingSettings(
            enabled=True,
            primary_url=None,
        )
        fake_detector = FakePrimaryURLDetector(primary_url="raft-primary.local:20202")
        resolver = PrimaryURLResolver(
            forwarding=forwarding,
            primary_url_detector=fake_detector,
            scheme="http",
        )

        result = resolver.resolve()

        # Should fall back to Raft
        assert result == "http://raft-primary.local:20202"

    def test_returns_none_when_both_modes_unavailable(self) -> None:
        """Test that None is returned when neither mode can resolve URL."""
        forwarding = ForwardingSettings(
            enabled=False,
        )
        fake_detector = FakePrimaryURLDetector(primary_url=None)
        resolver = PrimaryURLResolver(
            forwarding=forwarding,
            primary_url_detector=fake_detector,
        )

        result = resolver.resolve()

        assert result is None
