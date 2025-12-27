"""Django management command to display LiteFS status."""

import json
from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.health_checker import HealthChecker
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
            help="Show additional cluster status information (deprecated, use -v 2)",
        )
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            dest="format",
            help="Output format: text (default) or json",
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
        verbosity = options.get("verbosity", 1)
        verbose_flag = options.get("verbose", False)
        output_format = options.get("format", "text")

        # --verbose flag is equivalent to verbosity >= 2
        if verbose_flag:
            verbosity = max(verbosity, 2)

        try:
            # Get LiteFS settings from Django configuration
            django_settings = getattr(settings, "LITEFS", {})
            litefs_settings = get_litefs_settings(django_settings)
        except LiteFSConfigError as e:
            if output_format == "json":
                self._output_json(
                    {"error": str(e), "enabled": None, "role": None}, error=True
                )
                return
            raise CommandError(f"Invalid LiteFS configuration: {e}") from e

        # Check if LiteFS is enabled
        if not litefs_settings.enabled:
            if output_format == "json":
                self._output_json(
                    {
                        "enabled": False,
                        "mount_path": str(litefs_settings.mount_path),
                        "leader_election": litefs_settings.leader_election,
                    }
                )
                return
            if verbosity >= 1:
                self.stdout.write(
                    self.style.WARNING(
                        "LiteFS is disabled in settings (LITEFS.ENABLED=False)"
                    )
                )
            return

        # Determine node role and health status
        try:
            detector = PrimaryDetector(litefs_settings.mount_path)
            is_primary = detector.is_primary()
            role = "primary" if is_primary else "replica"

            # Get health status from HealthChecker
            health_checker = HealthChecker(detector)
            health_status = health_checker.check_health()
        except LiteFSNotRunningError as e:
            if output_format == "json":
                self._output_json(
                    {
                        "error": str(e),
                        "enabled": True,
                        "mount_path": str(litefs_settings.mount_path),
                        "role": None,
                    },
                    error=True,
                )
                return
            raise CommandError(f"LiteFS is not running: {e}") from e

        # Output based on format
        if output_format == "json":
            data = {
                "role": role,
                "mount_path": str(litefs_settings.mount_path),
                "enabled": True,
                "leader_election": litefs_settings.leader_election,
                "health_status": health_status.state,
            }
            if verbosity >= 2:
                data.update(
                    {
                        "data_path": str(litefs_settings.data_path),
                        "database_name": litefs_settings.database_name,
                        "proxy_addr": litefs_settings.proxy_addr,
                        "retention": litefs_settings.retention,
                    }
                )
            self._output_json(data)
            return

        # Text output based on verbosity
        if verbosity == 0:
            # Silent mode - no output
            return

        # verbosity >= 1: normal output
        role_display = "Primary" if role == "primary" else "Replica"
        health_display = health_status.state.capitalize()
        self.stdout.write(self.style.SUCCESS("LiteFS Status:"))
        self.stdout.write(f"  Node Role:     {role_display}")
        self.stdout.write(f"  Mount Path:    {litefs_settings.mount_path}")
        self.stdout.write("  Enabled:       True")
        self.stdout.write(f"  Leader Mode:   {litefs_settings.leader_election.upper()}")
        self.stdout.write(f"  Health:        {health_display}")

        # verbosity >= 2: detailed output
        if verbosity >= 2:
            self.stdout.write(f"  Data Path:     {litefs_settings.data_path}")
            self.stdout.write(f"  Database Name: {litefs_settings.database_name}")
            self.stdout.write(f"  Proxy Address: {litefs_settings.proxy_addr}")
            self.stdout.write(f"  Retention:     {litefs_settings.retention}")

    def _output_json(self, data: dict[str, Any], error: bool = False) -> None:
        """Output data as JSON."""
        self.stdout.write(json.dumps(data, indent=2))
