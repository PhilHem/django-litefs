"""Fake adapters for unit testing.

These in-memory fakes replace real implementations that require I/O
(filesystem, network, database) for fast, isolated unit tests.
"""

from __future__ import annotations


class FakePrimaryDetector:
    """In-memory fake for PrimaryDetector - no filesystem access.

    Use this instead of mocking PrimaryDetector in unit tests for:
    - Faster test execution (no filesystem I/O)
    - Cleaner test code (no mock.patch boilerplate)
    - Stateful testing (toggle primary/replica during test)
    - Error injection (simulate LiteFS failures)

    Implements PrimaryDetectorPort protocol for type safety.

    Example:
        def test_write_on_replica(fake_primary_detector):
            fake_primary_detector.set_primary(False)
            cursor = LiteFSCursor(conn, fake_primary_detector)
            with pytest.raises(NotPrimaryError):
                cursor.execute("INSERT ...")
    """

    def __init__(
        self, mount_path: str | None = None, *, is_primary: bool = True
    ) -> None:
        """Initialize with desired state.

        Args:
            mount_path: Ignored. Accepted for signature compatibility with
                PrimaryDetector. Allows this fake to be used as a drop-in
                replacement in tests.
            is_primary: Initial primary state (default True).
        """
        # mount_path is ignored - we're an in-memory fake
        self._mount_path = mount_path
        self._is_primary = is_primary
        self._error: Exception | None = None

    def is_primary(self) -> bool:
        """Return configured state or raise configured error.

        Returns:
            True if primary, False if replica.

        Raises:
            Exception: If error was set via set_error().
        """
        if self._error:
            raise self._error
        return self._is_primary

    def set_primary(self, is_primary: bool) -> None:
        """Set primary state for testing.

        Args:
            is_primary: New primary state.
        """
        self._is_primary = is_primary

    def set_error(self, error: Exception | None) -> None:
        """Set error to raise on next is_primary() call.

        Args:
            error: Exception to raise, or None to clear.
        """
        self._error = error
