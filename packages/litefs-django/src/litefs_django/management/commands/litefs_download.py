"""Django management command to download LiteFS binary."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from litefs.adapters.filesystem_binary_resolver import FilesystemBinaryResolver
from litefs.adapters.httpx_binary_downloader import HttpxBinaryDownloader
from litefs.adapters.platform_detector import OsPlatformDetector
from litefs.domain.binary import BinaryVersion
from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.binary_downloader import BinaryDownloader

# LiteFS release URL template
LITEFS_RELEASE_URL = (
    "https://github.com/superfly/litefs/releases/download/"
    "v{version}/litefs-v{version}-{os}-{arch}.tar.gz"
)

# Default LiteFS version to download
DEFAULT_LITEFS_VERSION = "0.5.11"


class Command(BaseCommand):
    """Download and install LiteFS binary for the current platform."""

    help = "Download LiteFS binary for the current platform"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Force re-download even if binary already exists",
        )
        parser.add_argument(
            "--version",
            type=str,
            dest="version",
            default=DEFAULT_LITEFS_VERSION,
            help=f"LiteFS version to download (default: {DEFAULT_LITEFS_VERSION})",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the download command.

        Downloads the LiteFS binary for the current platform unless it already
        exists (use --force to override).

        Args:
            *args: Variable length argument list (unused)
            **options: Arbitrary keyword arguments containing command options

        Raises:
            CommandError: If platform detection fails or download fails
        """
        force = options.get("force", False)
        version_str = options.get("version", DEFAULT_LITEFS_VERSION)

        # Step 1: Detect platform
        try:
            platform_detector = OsPlatformDetector()
            platform = platform_detector.detect()
        except LiteFSConfigError as e:
            raise CommandError(f"Unsupported platform: {e}") from e

        self.stdout.write(f"Detected platform: {platform.os}/{platform.arch}")

        # Step 2: Check if binary already exists
        resolver = FilesystemBinaryResolver()
        existing = resolver.resolve()

        if existing is not None and not force:
            self.stdout.write(
                self.style.SUCCESS(
                    f"LiteFS binary already exists at: {existing.path}\n"
                    f"Use --force to re-download."
                )
            )
            return

        # Step 3: Prepare download
        version = BinaryVersion.from_string(version_str)
        download_url = LITEFS_RELEASE_URL.format(
            version=version_str,
            os=platform.os,
            arch=platform.arch,
        )

        # Determine destination path
        destination = self._get_destination_path()

        self.stdout.write(f"Downloading LiteFS v{version} from:")
        self.stdout.write(f"  {download_url}")
        self.stdout.write(f"Destination: {destination}")

        # Step 4: Create adapter and use case
        httpx_downloader = HttpxBinaryDownloader(platform=platform, version=version)
        downloader = BinaryDownloader(port=httpx_downloader)

        # Step 5: Download binary
        result = downloader.download(download_url, destination)

        if not result.success:
            raise CommandError(f"Download failed: {result.error}")

        # Step 6: Report success
        metadata = result.metadata
        assert metadata is not None  # Guaranteed by success=True

        self.stdout.write(self.style.SUCCESS("Download complete!"))
        self.stdout.write(f"  Location: {metadata.location.path}")
        if metadata.size_bytes:
            size_mb = metadata.size_bytes / (1024 * 1024)
            self.stdout.write(f"  Size: {size_mb:.2f} MB")
        if metadata.checksum:
            self.stdout.write(f"  SHA256: {metadata.checksum[:16]}...")

    def _get_destination_path(self) -> Path:
        """Get the destination path for the downloaded binary.

        Returns platform-specific cache directory:
        - Linux: $XDG_CACHE_HOME/litefs/bin or ~/.cache/litefs/bin
        - macOS: ~/Library/Caches/litefs/bin

        Returns:
            Path to the destination file.
        """
        home = Path(os.environ.get("HOME", "~")).expanduser()

        if sys.platform == "darwin":
            cache_dir = home / "Library" / "Caches" / "litefs" / "bin"
        else:
            # Linux and other Unix-like systems
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                cache_dir = Path(xdg_cache) / "litefs" / "bin"
            else:
                cache_dir = home / ".cache" / "litefs" / "bin"

        # Create directory if it doesn't exist
        cache_dir.mkdir(parents=True, exist_ok=True)

        return cache_dir / "litefs"
