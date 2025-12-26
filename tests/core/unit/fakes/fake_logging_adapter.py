"""Fake logging adapter for testing."""

from __future__ import annotations


class FakeLoggingAdapter:
    """Fake logging adapter that captures log messages for assertion.

    Implements LoggingPort protocol by storing warning messages in a list
    for later retrieval and assertion in tests.

    Example:
        logger = FakeLoggingAdapter()
        some_use_case.execute(logger=logger)
        assert "expected warning" in logger.warnings
    """

    def __init__(self) -> None:
        """Initialize with empty warnings list."""
        self._warnings: list[str] = []

    def warning(self, message: str) -> None:
        """Store a warning message.

        Args:
            message: The warning message to store.
        """
        self._warnings.append(message)

    @property
    def warnings(self) -> list[str]:
        """Get a copy of captured warning messages.

        Returns:
            A copy of the list of captured warnings.
        """
        return list(self._warnings)

    def clear(self) -> None:
        """Clear all captured warning messages."""
        self._warnings.clear()
