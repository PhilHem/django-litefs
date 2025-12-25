"""Django management command to display LiteFS status."""

from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs_django.settings import get_litefs_settings
from litefs.domain.exceptions import LiteFSConfigError


class Command(BaseCommand):
    """Show LiteFS node role, mount path, and enabled state."""

    help = "Display LiteFS status: node role (primary/replica), mount path, and enabled state"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Show additional cluster status information",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the status command.

        Reads LiteFS settings from Django configuration and queries the
        LiteFS mount to determine current node role (primary or replica).

        Args:
            *args: Variable length argument list (unused)
            **options: Arbitrary keyword arguments containing command options

        Raises:
            CommandError: If LiteFS settings are invalid or not configured
            LiteFSNotRunningError: If LiteFS is not running
        """
        verbose = options.get("verbose", False)

        try:
            # Get LiteFS settings from Django configuration
            django_settings = getattr(settings, "LITEFS", {})
            litefs_settings = get_litefs_settings(django_settings)
        except LiteFSConfigError as e:
            raise CommandError(f"Invalid LiteFS configuration: {e}") from e

        # Check if LiteFS is enabled
        if not litefs_settings.enabled:
            self.stdout.write(
                self.style.WARNING(
                    "LiteFS is disabled in settings (LITEFS.ENABLED=False)"
                )
            )
            return

        # Determine node role
        try:
            detector = PrimaryDetector(litefs_settings.mount_path)
            is_primary = detector.is_primary()
            role = "Primary" if is_primary else "Replica"
        except LiteFSNotRunningError as e:
            raise CommandError(f"LiteFS is not running: {e}") from e

        # Output status information
        self.stdout.write(self.style.SUCCESS("LiteFS Status:"))
        self.stdout.write(f"  Node Role:     {role}")
        self.stdout.write(f"  Mount Path:    {litefs_settings.mount_path}")
        self.stdout.write("  Enabled:       True")
        self.stdout.write(f"  Leader Mode:   {litefs_settings.leader_election.upper()}")

        if verbose:
            self.stdout.write(f"  Data Path:     {litefs_settings.data_path}")
            self.stdout.write(f"  Database Name: {litefs_settings.database_name}")
            self.stdout.write(f"  Proxy Address: {litefs_settings.proxy_addr}")
            self.stdout.write(f"  Retention:     {litefs_settings.retention}")
