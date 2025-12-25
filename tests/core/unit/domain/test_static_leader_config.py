"""Unit tests for StaticLeaderConfig domain value object."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.settings import StaticLeaderConfig
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestStaticLeaderConfig:
    """Test StaticLeaderConfig value object."""

    def test_create_with_valid_hostname(self):
        """Test creating config with valid hostname."""
        config = StaticLeaderConfig(primary_hostname="node1")
        assert config.primary_hostname == "node1"

    def test_create_with_fqdn_hostname(self):
        """Test creating config with fully qualified domain name."""
        config = StaticLeaderConfig(primary_hostname="node1.example.com")
        assert config.primary_hostname == "node1.example.com"

    def test_create_with_hyphenated_hostname(self):
        """Test creating config with hyphenated hostname."""
        config = StaticLeaderConfig(primary_hostname="web-server-01")
        assert config.primary_hostname == "web-server-01"

    def test_frozen_dataclass(self):
        """Test that StaticLeaderConfig is immutable."""
        config = StaticLeaderConfig(primary_hostname="node1")
        with pytest.raises(AttributeError):
            config.primary_hostname = "node2"  # type: ignore

    def test_reject_empty_hostname(self):
        """Test that empty hostname is rejected."""
        with pytest.raises(LiteFSConfigError, match="cannot be empty"):
            StaticLeaderConfig(primary_hostname="")

    def test_reject_whitespace_only_hostname(self):
        """Test that whitespace-only hostname is rejected."""
        with pytest.raises(LiteFSConfigError, match="whitespace-only"):
            StaticLeaderConfig(primary_hostname="   ")

    def test_reject_leading_whitespace(self):
        """Test that leading whitespace is rejected."""
        with pytest.raises(LiteFSConfigError, match="leading/trailing whitespace"):
            StaticLeaderConfig(primary_hostname=" node1")

    def test_reject_trailing_whitespace(self):
        """Test that trailing whitespace is rejected."""
        with pytest.raises(LiteFSConfigError, match="leading/trailing whitespace"):
            StaticLeaderConfig(primary_hostname="node1 ")

    def test_reject_null_byte(self):
        """Test that null byte is rejected."""
        with pytest.raises(LiteFSConfigError, match="control characters"):
            StaticLeaderConfig(primary_hostname="node1\x00")

    def test_reject_control_characters(self):
        """Test that control characters are rejected."""
        with pytest.raises(LiteFSConfigError, match="control characters"):
            StaticLeaderConfig(primary_hostname="node1\n")

    def test_reject_tab_character(self):
        """Test that tab character is rejected."""
        with pytest.raises(LiteFSConfigError, match="control characters"):
            StaticLeaderConfig(primary_hostname="node1\t")

    def test_reject_delete_character(self):
        """Test that DEL character (0x7F) is rejected."""
        with pytest.raises(LiteFSConfigError, match="control characters"):
            StaticLeaderConfig(primary_hostname="node1\x7f")

    def test_equality(self):
        """Test that configs with same hostname are equal."""
        config1 = StaticLeaderConfig(primary_hostname="node1")
        config2 = StaticLeaderConfig(primary_hostname="node1")
        assert config1 == config2

    def test_inequality(self):
        """Test that configs with different hostnames are not equal."""
        config1 = StaticLeaderConfig(primary_hostname="node1")
        config2 = StaticLeaderConfig(primary_hostname="node2")
        assert config1 != config2

    def test_hash_consistency(self):
        """Test that configs with same hostname have same hash."""
        config1 = StaticLeaderConfig(primary_hostname="node1")
        config2 = StaticLeaderConfig(primary_hostname="node1")
        assert hash(config1) == hash(config2)

    def test_can_use_in_set(self):
        """Test that StaticLeaderConfig can be used in sets."""
        config1 = StaticLeaderConfig(primary_hostname="node1")
        config2 = StaticLeaderConfig(primary_hostname="node1")
        config3 = StaticLeaderConfig(primary_hostname="node2")

        config_set = {config1, config2, config3}
        assert len(config_set) == 2  # config1 and config2 are equal


@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
class TestStaticLeaderConfigPBT:
    """Property-based tests for StaticLeaderConfig."""

    @given(
        hostname=st.text(
            alphabet=st.characters(
                min_codepoint=33,  # Start after control chars and space
                max_codepoint=126,  # End before DEL
                blacklist_characters=" \t\n\r",  # Exclude whitespace
            ),
            min_size=1,
            max_size=253,  # DNS hostname max length
        )
    )
    def test_valid_ascii_hostnames_accepted(self, hostname):
        """PBT: Valid ASCII hostnames should be accepted."""
        config = StaticLeaderConfig(primary_hostname=hostname)
        assert config.primary_hostname == hostname

    @given(
        hostname=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs"),  # Control + surrogate
                blacklist_characters=" \t\n\r\x7f",  # Whitespace + DEL
            ),
            min_size=1,
            max_size=253,
        )
    )
    def test_unicode_hostnames_without_control_chars_accepted(self, hostname):
        """PBT: Unicode hostnames without control chars should be accepted."""
        # Skip if hostname is whitespace-only or has leading/trailing whitespace
        if not hostname.strip() or hostname != hostname.strip():
            return

        config = StaticLeaderConfig(primary_hostname=hostname)
        assert config.primary_hostname == hostname

    @given(
        hostname_base=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        ),
        control_char=st.sampled_from(["\x00", "\x01", "\x1f", "\x7f", "\n", "\t"]),
    )
    def test_hostnames_with_control_chars_rejected(self, hostname_base, control_char):
        """PBT: Hostnames with control characters should be rejected."""
        hostname_with_control = hostname_base + control_char

        with pytest.raises(LiteFSConfigError):
            StaticLeaderConfig(primary_hostname=hostname_with_control)

    @given(
        whitespace=st.sampled_from([" ", "  ", "   ", "\t", " \t ", "\t\t"])
    )
    def test_whitespace_only_rejected(self, whitespace):
        """PBT: Whitespace-only hostnames should be rejected."""
        with pytest.raises(LiteFSConfigError):
            StaticLeaderConfig(primary_hostname=whitespace)

    @given(
        hostname=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        ),
        prefix_ws=st.sampled_from([" ", "  ", "\t", " \t"]),
    )
    def test_leading_whitespace_rejected(self, hostname, prefix_ws):
        """PBT: Hostnames with leading whitespace should be rejected."""
        hostname_with_ws = prefix_ws + hostname

        with pytest.raises(LiteFSConfigError):
            StaticLeaderConfig(primary_hostname=hostname_with_ws)

    @given(
        hostname=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        ),
        suffix_ws=st.sampled_from([" ", "  ", "\t", " \t"]),
    )
    def test_trailing_whitespace_rejected(self, hostname, suffix_ws):
        """PBT: Hostnames with trailing whitespace should be rejected."""
        hostname_with_ws = hostname + suffix_ws

        with pytest.raises(LiteFSConfigError):
            StaticLeaderConfig(primary_hostname=hostname_with_ws)

    @given(
        hostname=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126),
            min_size=1,
            max_size=50,
        )
    )
    def test_idempotent_creation(self, hostname):
        """PBT: Creating config with same hostname should be idempotent."""
        config1 = StaticLeaderConfig(primary_hostname=hostname)
        config2 = StaticLeaderConfig(primary_hostname=hostname)

        assert config1 == config2
        assert hash(config1) == hash(config2)
