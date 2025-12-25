"""Django management command for LiteFS health checks."""

from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs_django.settings import get_litefs_settings
from litefs.domain.exceptions import LiteFSConfigError


class Command(BaseCommand):
    """Perform health checks suitable for deployment readiness."""

    help = "Perform LiteFS health checks for deployment readiness (exit 0 on success, non-zero on failure)"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Show detailed health check results",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute health checks.

        Performs the following checks:
        1. LiteFS configuration is valid and complete
        2. LiteFS is enabled
        3. LiteFS mount path is accessible and mounted
        4. Current node role can be determined (primary or replica)

        Returns:
            None on success (exit code 0)

        Raises:
            CommandError: If any health check fails (non-zero exit code)
            LiteFSNotRunningError: If LiteFS is not running (non-zero exit code)
            LiteFSConfigError: If configuration is invalid (non-zero exit code)
        """
        verbose = options.get("verbose", False)

        # Health Check 1: Validate configuration
        if verbose:
            self.stdout.write("Performing health checks...")
            self.stdout.write("  [1/4] Validating LiteFS configuration...")

        try:
            django_settings = getattr(settings, "LITEFS", {})
            litefs_settings = get_litefs_settings(django_settings)
        except LiteFSConfigError as e:
            raise CommandError(f"FAIL: Invalid LiteFS configuration: {e}") from e

        # Health Check 2: Verify LiteFS is enabled
        if verbose:
            self.stdout.write("  [2/4] Checking if LiteFS is enabled...")

        if not litefs_settings.enabled:
            raise CommandError(
                "FAIL: LiteFS is disabled (LITEFS.ENABLED=False). "
                "Enable LiteFS before deployment."
            )

        if verbose:
            self.stdout.write("        OK - LiteFS is enabled")

        # Health Check 3: Verify mount path is accessible
        if verbose:
            self.stdout.write("  [3/4] Checking mount path accessibility...")

        try:
            detector = PrimaryDetector(litefs_settings.mount_path)
        except Exception as e:
            raise CommandError(f"FAIL: Cannot access LiteFS mount path: {e}") from e

        if verbose:
            self.stdout.write(
                f"        OK - Mount path accessible ({litefs_settings.mount_path})"
            )

        # Health Check 4: Determine node role (verifies LiteFS is running)
        if verbose:
            self.stdout.write(
                "  [4/4] Checking node role (verifies LiteFS is running)..."
            )

        try:
            is_primary = detector.is_primary()
            role = "primary" if is_primary else "replica"
        except LiteFSNotRunningError as e:
            raise CommandError(
                f"FAIL: LiteFS is not running or mount path is inaccessible: {e}"
            ) from e

        # All checks passed
        if verbose:
            self.stdout.write(f"        OK - Node role is {role}")
            self.stdout.write(self.style.SUCCESS("All health checks passed!"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"LiteFS health check passed (node: {role})")
            )
