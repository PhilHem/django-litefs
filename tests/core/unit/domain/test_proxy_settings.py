"""Unit tests for ProxySettings domain value object."""

import pytest
from hypothesis import given, strategies as st

from litefs.domain.settings import ProxySettings
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
class TestProxySettings:
    """Test ProxySettings value object."""

    def test_create_with_valid_config(self) -> None:
        """Test creating config with valid required fields."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy.addr == ":8080"
        assert proxy.target == "localhost:8081"
        assert proxy.db == "db.sqlite3"
        assert proxy.passthrough == []
        assert proxy.primary_redirect_timeout == "5s"

    def test_create_with_all_fields(self) -> None:
        """Test creating config with all fields specified."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
            passthrough=["/static/*", "*.css"],
            primary_redirect_timeout="10s",
        )
        assert proxy.addr == ":8080"
        assert proxy.target == "localhost:8081"
        assert proxy.db == "db.sqlite3"
        assert proxy.passthrough == ["/static/*", "*.css"]
        assert proxy.primary_redirect_timeout == "10s"

    def test_frozen_dataclass(self) -> None:
        """Test that ProxySettings is immutable."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        with pytest.raises(AttributeError):
            proxy.addr = ":9090"  # type: ignore

    def test_reject_empty_addr(self) -> None:
        """Test that empty addr is rejected."""
        with pytest.raises(LiteFSConfigError, match="addr cannot be empty"):
            ProxySettings(
                addr="",
                target="localhost:8081",
                db="db.sqlite3",
            )

    def test_reject_whitespace_only_addr(self) -> None:
        """Test that whitespace-only addr is rejected."""
        with pytest.raises(LiteFSConfigError, match="whitespace-only"):
            ProxySettings(
                addr="   ",
                target="localhost:8081",
                db="db.sqlite3",
            )

    def test_reject_empty_target(self) -> None:
        """Test that empty target is rejected."""
        with pytest.raises(LiteFSConfigError, match="target cannot be empty"):
            ProxySettings(
                addr=":8080",
                target="",
                db="db.sqlite3",
            )

    def test_reject_whitespace_only_target(self) -> None:
        """Test that whitespace-only target is rejected."""
        with pytest.raises(LiteFSConfigError, match="whitespace-only"):
            ProxySettings(
                addr=":8080",
                target="   ",
                db="db.sqlite3",
            )

    def test_reject_empty_db(self) -> None:
        """Test that empty db is rejected."""
        with pytest.raises(LiteFSConfigError, match="db cannot be empty"):
            ProxySettings(
                addr=":8080",
                target="localhost:8081",
                db="",
            )

    def test_reject_whitespace_only_db(self) -> None:
        """Test that whitespace-only db is rejected."""
        with pytest.raises(LiteFSConfigError, match="whitespace-only"):
            ProxySettings(
                addr=":8080",
                target="localhost:8081",
                db="   ",
            )

    def test_equality(self) -> None:
        """Test that configs with same values are equal."""
        proxy1 = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        proxy2 = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy1 == proxy2

    def test_inequality(self) -> None:
        """Test that configs with different values are not equal."""
        proxy1 = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        proxy2 = ProxySettings(
            addr=":9090",
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy1 != proxy2

    def test_is_unhashable_due_to_mutable_list(self) -> None:
        """Test that ProxySettings is unhashable due to mutable passthrough list.

        Frozen dataclasses with mutable default fields cannot be hashed.
        This is expected behavior to prevent accidental mutation after creation.
        """
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        with pytest.raises(TypeError, match="unhashable"):
            hash(proxy)

    def test_passthrough_defaults_to_empty_list(self) -> None:
        """Test that passthrough defaults to empty list."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy.passthrough == []
        assert isinstance(proxy.passthrough, list)

    def test_primary_redirect_timeout_defaults_to_5s(self) -> None:
        """Test that primary_redirect_timeout defaults to '5s'."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy.primary_redirect_timeout == "5s"


@pytest.mark.unit
@pytest.mark.tier(3)
@pytest.mark.tra("Domain.Invariant")
@pytest.mark.property
class TestProxySettingsPBT:
    """Property-based tests for ProxySettings."""

    @given(
        addr=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_valid_non_whitespace_addr_accepted(self, addr: str) -> None:
        """PBT: Valid non-whitespace addr should be accepted."""
        proxy = ProxySettings(
            addr=addr,
            target="localhost:8081",
            db="db.sqlite3",
        )
        assert proxy.addr == addr

    @given(
        target=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_valid_non_whitespace_target_accepted(self, target: str) -> None:
        """PBT: Valid non-whitespace target should be accepted."""
        proxy = ProxySettings(
            addr=":8080",
            target=target,
            db="db.sqlite3",
        )
        assert proxy.target == target

    @given(
        db=st.text(
            alphabet=st.characters(
                min_codepoint=33,
                max_codepoint=126,
                blacklist_characters=" \t\n\r",
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_valid_non_whitespace_db_accepted(self, db: str) -> None:
        """PBT: Valid non-whitespace db should be accepted."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db=db,
        )
        assert proxy.db == db

    @given(
        passthrough=st.lists(
            st.text(
                alphabet=st.characters(min_codepoint=33, max_codepoint=126),
                min_size=1,
                max_size=50,
            ),
            max_size=10,
        )
    )
    def test_passthrough_patterns_accepted(self, passthrough: list[str]) -> None:
        """PBT: Any passthrough patterns should be accepted."""
        proxy = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
            passthrough=passthrough,
        )
        assert proxy.passthrough == passthrough

    def test_idempotent_creation(self) -> None:
        """PBT: Creating config with same values should be idempotent."""
        proxy1 = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )
        proxy2 = ProxySettings(
            addr=":8080",
            target="localhost:8081",
            db="db.sqlite3",
        )

        assert proxy1 == proxy2
