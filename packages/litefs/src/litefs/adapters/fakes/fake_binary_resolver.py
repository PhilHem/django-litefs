"""Fake binary resolver for testing.

Provides a test double for BinaryResolverPort that returns
preconfigured values without filesystem operations.
"""

from __future__ import annotations

from litefs.domain.binary import BinaryLocation


class FakeBinaryResolver:
    """Fake implementation of BinaryResolverPort for testing.

    Returns a preconfigured BinaryLocation or None without
    performing any filesystem operations.

    Example:
        >>> from pathlib import Path
        >>> location = BinaryLocation(path=Path("/usr/bin/litefs"), is_custom=False)
        >>> fake = FakeBinaryResolver(location=location)
        >>> fake.resolve()
        BinaryLocation(path=PosixPath('/usr/bin/litefs'), is_custom=False)
    """

    def __init__(self, location: BinaryLocation | None) -> None:
        """Initialize with preconfigured return value.

        Args:
            location: BinaryLocation to return from resolve(),
                or None to simulate binary not found.
        """
        self._location = location

    def resolve(self) -> BinaryLocation | None:
        """Return the preconfigured BinaryLocation.

        Returns:
            The BinaryLocation provided at construction, or None.
        """
        return self._location
