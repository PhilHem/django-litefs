"""Unit tests for FilesystemBinaryResolver adapter."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from litefs.adapters.filesystem_binary_resolver import FilesystemBinaryResolver
from litefs.adapters.ports import BinaryResolverPort


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FilesystemBinaryResolver")
class TestFilesystemBinaryResolver:
    """Test FilesystemBinaryResolver implementation."""

    def test_satisfies_protocol(self) -> None:
        """Test that FilesystemBinaryResolver satisfies BinaryResolverPort protocol."""
        resolver = FilesystemBinaryResolver()
        assert isinstance(resolver, BinaryResolverPort)

    def test_resolve_returns_none_when_binary_not_found(
        self, tmp_path: Path
    ) -> None:
        """Test that resolve() returns None when binary is not found anywhere."""
        resolver = FilesystemBinaryResolver()

        # Mock all search locations to return non-existent paths
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(resolver, "_get_path_locations", return_value=[]):
                with patch.object(resolver, "_get_cache_dir", return_value=tmp_path / "nonexistent"):
                    result = resolver.resolve()

        assert result is None

    def test_resolve_from_env_var_returns_custom_location(
        self, tmp_path: Path
    ) -> None:
        """Test that resolve() finds binary from LITEFS_BINARY_PATH env var."""
        binary_path = tmp_path / "custom" / "litefs"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {"LITEFS_BINARY_PATH": str(binary_path)}):
            result = resolver.resolve()

        assert result is not None
        assert result.path == binary_path
        assert result.is_custom is True

    def test_resolve_from_path_returns_default_location(
        self, tmp_path: Path
    ) -> None:
        """Test that resolve() finds binary from system PATH."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        binary_path = bin_dir / "litefs"
        binary_path.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {"PATH": str(bin_dir)}, clear=False):
            with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "LITEFS_BINARY_PATH"}):
                # Remove LITEFS_BINARY_PATH if present
                env_without_custom = {k: v for k, v in os.environ.items() if k != "LITEFS_BINARY_PATH"}
                env_without_custom["PATH"] = str(bin_dir)
                with patch.dict(os.environ, env_without_custom, clear=True):
                    result = resolver.resolve()

        assert result is not None
        assert result.path == binary_path
        assert result.is_custom is False

    def test_resolve_from_cache_dir_linux(self, tmp_path: Path) -> None:
        """Test that resolve() finds binary from Linux cache directory."""
        cache_dir = tmp_path / ".cache" / "litefs" / "bin"
        cache_dir.mkdir(parents=True)
        binary_path = cache_dir / "litefs"
        binary_path.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(resolver, "_get_path_locations", return_value=[]):
                with patch.object(resolver, "_get_cache_dir", return_value=cache_dir):
                    result = resolver.resolve()

        assert result is not None
        assert result.path == binary_path
        assert result.is_custom is False

    def test_resolve_from_cache_dir_macos(self, tmp_path: Path) -> None:
        """Test that resolve() finds binary from macOS cache directory."""
        cache_dir = tmp_path / "Library" / "Caches" / "litefs" / "bin"
        cache_dir.mkdir(parents=True)
        binary_path = cache_dir / "litefs"
        binary_path.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(resolver, "_get_path_locations", return_value=[]):
                with patch.object(resolver, "_get_cache_dir", return_value=cache_dir):
                    result = resolver.resolve()

        assert result is not None
        assert result.path == binary_path
        assert result.is_custom is False

    def test_env_var_takes_priority(self, tmp_path: Path) -> None:
        """Test that LITEFS_BINARY_PATH takes priority over other locations."""
        # Create binary in PATH
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        path_binary = bin_dir / "litefs"
        path_binary.touch()

        # Create binary in custom location
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        custom_binary = custom_dir / "litefs"
        custom_binary.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {
            "LITEFS_BINARY_PATH": str(custom_binary),
            "PATH": str(bin_dir),
        }, clear=True):
            result = resolver.resolve()

        assert result is not None
        assert result.path == custom_binary
        assert result.is_custom is True

    def test_resolve_skips_nonexistent_env_var_path(self, tmp_path: Path) -> None:
        """Test that resolve() skips non-existent LITEFS_BINARY_PATH."""
        # Create binary in PATH as fallback
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        path_binary = bin_dir / "litefs"
        path_binary.touch()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {
            "LITEFS_BINARY_PATH": str(tmp_path / "nonexistent" / "litefs"),
            "PATH": str(bin_dir),
        }, clear=True):
            result = resolver.resolve()

        assert result is not None
        assert result.path == path_binary
        assert result.is_custom is False

    def test_resolve_skips_nonexistent_path_entries(self, tmp_path: Path) -> None:
        """Test that resolve() skips non-existent PATH directories."""
        # Create binary in second PATH entry
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        path_binary = bin_dir / "litefs"
        path_binary.touch()

        resolver = FilesystemBinaryResolver()

        # First path entry doesn't exist
        nonexistent = tmp_path / "nonexistent"

        with patch.dict(os.environ, {
            "PATH": f"{nonexistent}:{bin_dir}",
        }, clear=True):
            result = resolver.resolve()

        assert result is not None
        assert result.path == path_binary
        assert result.is_custom is False


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FilesystemBinaryResolver.CacheDir")
class TestFilesystemBinaryResolverCacheDir:
    """Test cache directory detection logic."""

    def test_get_cache_dir_linux(self) -> None:
        """Test _get_cache_dir returns correct path on Linux."""
        resolver = FilesystemBinaryResolver()

        with patch("sys.platform", "linux"):
            with patch.dict(os.environ, {"HOME": "/home/testuser"}, clear=True):
                result = resolver._get_cache_dir()

        assert result == Path("/home/testuser/.cache/litefs/bin")

    def test_get_cache_dir_macos(self) -> None:
        """Test _get_cache_dir returns correct path on macOS."""
        resolver = FilesystemBinaryResolver()

        with patch("sys.platform", "darwin"):
            with patch.dict(os.environ, {"HOME": "/Users/testuser"}, clear=True):
                result = resolver._get_cache_dir()

        assert result == Path("/Users/testuser/Library/Caches/litefs/bin")

    def test_get_cache_dir_uses_xdg_cache_home_when_set(self) -> None:
        """Test _get_cache_dir respects XDG_CACHE_HOME on Linux."""
        resolver = FilesystemBinaryResolver()

        with patch("sys.platform", "linux"):
            with patch.dict(os.environ, {
                "HOME": "/home/testuser",
                "XDG_CACHE_HOME": "/custom/cache",
            }, clear=True):
                result = resolver._get_cache_dir()

        assert result == Path("/custom/cache/litefs/bin")


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.FilesystemBinaryResolver.PathLocations")
class TestFilesystemBinaryResolverPathLocations:
    """Test PATH location detection logic."""

    def test_get_path_locations_returns_list(self, tmp_path: Path) -> None:
        """Test _get_path_locations returns list of paths."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {"PATH": str(bin_dir)}, clear=True):
            result = resolver._get_path_locations()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == bin_dir / "litefs"

    def test_get_path_locations_handles_multiple_entries(self, tmp_path: Path) -> None:
        """Test _get_path_locations handles multiple PATH entries."""
        bin1 = tmp_path / "bin1"
        bin2 = tmp_path / "bin2"
        bin1.mkdir()
        bin2.mkdir()

        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {"PATH": f"{bin1}:{bin2}"}, clear=True):
            result = resolver._get_path_locations()

        assert len(result) == 2
        assert result[0] == bin1 / "litefs"
        assert result[1] == bin2 / "litefs"

    def test_get_path_locations_returns_empty_when_no_path(self) -> None:
        """Test _get_path_locations returns empty list when PATH not set."""
        resolver = FilesystemBinaryResolver()

        with patch.dict(os.environ, {}, clear=True):
            result = resolver._get_path_locations()

        assert result == []
