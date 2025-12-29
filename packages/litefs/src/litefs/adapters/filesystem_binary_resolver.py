"""Filesystem binary resolver adapter.

Implements BinaryResolverPort to search for existing LiteFS binary
on the filesystem. Does NOT download - only finds existing binaries.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from litefs.domain.binary import BinaryLocation


class FilesystemBinaryResolver:
    """Adapter that searches for existing LiteFS binary on filesystem.

    Searches in priority order:
    1. LITEFS_BINARY_PATH environment variable (custom location)
    2. System PATH entries (default location)
    3. User cache directory (default location)

    Does NOT download or install the binary - only finds existing ones.
    """

    def resolve(self) -> BinaryLocation | None:
        """Resolve/find an existing LiteFS binary on the filesystem.

        Returns:
            BinaryLocation if the binary is found, containing:
            - path: Path to the binary location
            - is_custom: True if user-specified via env var, False if default location
            None if the binary is not found on the filesystem.
        """
        # Priority 1: Check environment variable (custom location)
        env_path = os.environ.get("LITEFS_BINARY_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return BinaryLocation(path=path, is_custom=True)

        # Priority 2: Check system PATH (default locations)
        for path in self._get_path_locations():
            if path.exists():
                return BinaryLocation(path=path, is_custom=False)

        # Priority 3: Check user cache directory (default location)
        cache_dir = self._get_cache_dir()
        cache_binary = cache_dir / "litefs"
        if cache_binary.exists():
            return BinaryLocation(path=cache_binary, is_custom=False)

        return None

    def _get_path_locations(self) -> list[Path]:
        """Get list of potential binary paths from system PATH.

        Returns:
            List of Path objects pointing to potential litefs binary locations.
        """
        path_env = os.environ.get("PATH", "")
        if not path_env:
            return []

        paths: list[Path] = []
        for dir_path in path_env.split(os.pathsep):
            if dir_path:
                paths.append(Path(dir_path) / "litefs")

        return paths

    def _get_cache_dir(self) -> Path:
        """Get the user cache directory for litefs binary.

        Returns platform-specific cache directory:
        - Linux: $XDG_CACHE_HOME/litefs/bin or ~/.cache/litefs/bin
        - macOS: ~/Library/Caches/litefs/bin

        Returns:
            Path to the cache directory for litefs binary.
        """
        home = Path(os.environ.get("HOME", "~")).expanduser()

        if sys.platform == "darwin":
            return home / "Library" / "Caches" / "litefs" / "bin"

        # Linux and other Unix-like systems
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / "litefs" / "bin"

        return home / ".cache" / "litefs" / "bin"
