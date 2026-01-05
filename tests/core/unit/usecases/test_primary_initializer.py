"""Unit tests for PrimaryInitializer use case."""

import pytest
from hypothesis import given, strategies as st

from litefs.usecases.primary_initializer import PrimaryInitializer
from litefs.domain.settings import StaticLeaderConfig


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase")
class TestPrimaryInitializer:
    """Test PrimaryInitializer use case."""

    def test_is_primary_when_hostname_matches(self):
        """Test that is_primary returns True when current hostname matches primary_hostname."""
        config = StaticLeaderConfig(primary_hostname="node1")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="node1") is True

    def test_is_not_primary_when_hostname_does_not_match(self):
        """Test that is_primary returns False when current hostname does not match."""
        config = StaticLeaderConfig(primary_hostname="node1")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="node2") is False

    def test_case_sensitive_hostname_comparison(self):
        """Test that hostname comparison is case-sensitive."""
        config = StaticLeaderConfig(primary_hostname="Node1")
        initializer = PrimaryInitializer(config=config)

        # Different case should not match
        assert initializer.is_primary(current_hostname="node1") is False
        assert initializer.is_primary(current_hostname="Node1") is True

    def test_exact_match_required(self):
        """Test that hostname must match exactly (no partial matches)."""
        config = StaticLeaderConfig(primary_hostname="node1")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="node1-replica") is False
        assert initializer.is_primary(current_hostname="node") is False

    def test_with_fqdn_hostnames(self):
        """Test with fully qualified domain names."""
        config = StaticLeaderConfig(primary_hostname="node1.example.com")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="node1.example.com") is True
        assert initializer.is_primary(current_hostname="node1") is False

    def test_with_hyphenated_hostnames(self):
        """Test with hyphenated hostnames."""
        config = StaticLeaderConfig(primary_hostname="web-server-01")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="web-server-01") is True
        assert initializer.is_primary(current_hostname="web-server-02") is False

    def test_with_numeric_hostnames(self):
        """Test with numeric hostnames."""
        config = StaticLeaderConfig(primary_hostname="192.168.1.1")
        initializer = PrimaryInitializer(config=config)

        assert initializer.is_primary(current_hostname="192.168.1.1") is True
        assert initializer.is_primary(current_hostname="192.168.1.2") is False

    def test_multiple_instances_same_config(self):
        """Test that multiple instances with same config behave identically."""
        config = StaticLeaderConfig(primary_hostname="node1")
        initializer1 = PrimaryInitializer(config=config)
        initializer2 = PrimaryInitializer(config=config)

        # Both should return same result for same hostname
        assert initializer1.is_primary(current_hostname="node1") is True
        assert initializer2.is_primary(current_hostname="node1") is True

    def test_stateless_behavior(self):
        """Test that initializer is stateless and doesn't maintain state between calls."""
        config = StaticLeaderConfig(primary_hostname="node1")
        initializer = PrimaryInitializer(config=config)

        # Call with different hostnames sequentially
        result1 = initializer.is_primary(current_hostname="node1")
        result2 = initializer.is_primary(current_hostname="node2")
        result3 = initializer.is_primary(current_hostname="node1")

        assert result1 is True
        assert result2 is False
        assert result3 is True  # Should return to True without side effects


@pytest.mark.tier(3)
@pytest.mark.tra("UseCase")
class TestPrimaryInitializerPBT:
    """Property-based tests for PrimaryInitializer."""

    @given(
        hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=253,
        )
    )
    def test_is_primary_idempotent(self, hostname):
        """PBT: is_primary should return same result when called multiple times."""
        config = StaticLeaderConfig(primary_hostname=hostname)
        initializer = PrimaryInitializer(config=config)

        # Call is_primary multiple times with same hostname
        result1 = initializer.is_primary(current_hostname=hostname)
        result2 = initializer.is_primary(current_hostname=hostname)
        result3 = initializer.is_primary(current_hostname=hostname)

        # All results should be identical
        assert result1 is True
        assert result2 is True
        assert result3 is True

    @given(
        primary_hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=253,
        ),
        current_hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=253,
        ),
    )
    def test_is_primary_consistency(self, primary_hostname, current_hostname):
        """PBT: is_primary result should be consistent with hostname equality."""
        config = StaticLeaderConfig(primary_hostname=primary_hostname)
        initializer = PrimaryInitializer(config=config)

        result = initializer.is_primary(current_hostname=current_hostname)

        # Result should match the equality check
        expected = primary_hostname == current_hostname
        assert result == expected

    @given(
        hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=253,
        )
    )
    def test_mismatch_returns_false_for_different_hostname(self, hostname):
        """PBT: is_primary should return False for different hostnames."""
        config = StaticLeaderConfig(primary_hostname=hostname)
        initializer = PrimaryInitializer(config=config)

        # Create a different hostname
        different_hostname = hostname + "_other"

        result = initializer.is_primary(current_hostname=different_hostname)
        assert result is False
