"""Tests for FakeLoggingAdapter."""

import pytest

from litefs.adapters.ports import LoggingPort
from .fake_logging_adapter import FakeLoggingAdapter


@pytest.mark.unit
@pytest.mark.tier(1)
@pytest.mark.tra("Contract.FakeLoggingAdapter")
class TestFakeLoggingAdapter:
    """Tests for FakeLoggingAdapter fake implementation."""

    def test_warning_stores_message(self) -> None:
        """warning() should store the message for later assertion."""
        adapter = FakeLoggingAdapter()
        adapter.warning("test warning message")
        assert adapter.warnings == ["test warning message"]

    def test_multiple_warnings_stored_in_order(self) -> None:
        """Multiple warnings should be stored in order."""
        adapter = FakeLoggingAdapter()
        adapter.warning("first")
        adapter.warning("second")
        adapter.warning("third")
        assert adapter.warnings == ["first", "second", "third"]

    def test_warnings_returns_copy(self) -> None:
        """warnings property should return a copy, not the internal list."""
        adapter = FakeLoggingAdapter()
        adapter.warning("original")
        warnings = adapter.warnings
        warnings.append("modified")
        assert adapter.warnings == ["original"]

    def test_clear_resets_messages(self) -> None:
        """clear() should reset all captured messages."""
        adapter = FakeLoggingAdapter()
        adapter.warning("to be cleared")
        adapter.warning("also cleared")
        adapter.clear()
        assert adapter.warnings == []

    def test_implements_logging_port_protocol(self) -> None:
        """FakeLoggingAdapter should implement LoggingPort protocol."""
        adapter = FakeLoggingAdapter()
        assert isinstance(adapter, LoggingPort)

    def test_empty_warnings_initially(self) -> None:
        """New adapter should have empty warnings list."""
        adapter = FakeLoggingAdapter()
        assert adapter.warnings == []
