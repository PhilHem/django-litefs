"""Django management command for LiteFS health checks."""

from dataclasses import dataclass
from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs_django.settings import get_litefs_settings
from litefs.domain.exceptions import LiteFSConfigError
from litefs.domain.settings import LiteFSSettings


@dataclass
class ConfigIssue:
    """Represents a configuration issue with a suggested fix."""

    description: str
    fix: str


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

    def _collect_issues(
        self, verbose: bool
    ) -> tuple[list[ConfigIssue], "LiteFSSettings | None", "PrimaryDetector | None"]:
        """Collect all configuration issues without failing fast.

        Returns:
            Tuple of (issues list, settings if valid, detector if created)
        """
        issues: list[ConfigIssue] = []
        litefs_settings = None
        detector = None

        # Health Check 1: Validate configuration
        if verbose:
            self.stdout.write("Performing health checks...")
            self.stdout.write("  [1/5] Validating LiteFS configuration...")

        try:
            django_settings = getattr(settings, "LITEFS", {})
            litefs_settings = get_litefs_settings(django_settings)
        except LiteFSConfigError as e:
            issues.append(
                ConfigIssue(
                    description=f"Invalid LiteFS configuration: {e}",
                    fix="Check your LITEFS settings dict in Django settings.",
                )
            )

        # Health Check 2: Validate database backend
        if verbose:
            self.stdout.write("  [2/5] Checking database backend configuration...")

        expected_backend = "litefs_django.db.backends.litefs"
        databases = getattr(settings, "DATABASES", {})
        default_db = databases.get("default", {})
        actual_backend = default_db.get("ENGINE", "")

        if actual_backend != expected_backend:
            issues.append(
                ConfigIssue(
                    description=(
                        f"Database backend is not configured correctly. "
                        f"Expected ENGINE '{expected_backend}', got '{actual_backend}'."
                    ),
                    fix="Update DATABASES['default']['ENGINE'] in settings.",
                )
            )
        elif verbose:
            self.stdout.write(f"        OK - Database backend is {expected_backend}")

        # Health Check 3: Verify LiteFS is enabled
        if verbose:
            self.stdout.write("  [3/5] Checking if LiteFS is enabled...")

        if litefs_settings is not None and not litefs_settings.enabled:
            issues.append(
                ConfigIssue(
                    description="LiteFS is disabled (LITEFS.ENABLED=False).",
                    fix="Enable LiteFS before deployment by setting LITEFS['ENABLED'] = True.",
                )
            )
        elif verbose and litefs_settings is not None:
            self.stdout.write("        OK - LiteFS is enabled")

        # Health Check 4: Verify mount path is accessible
        if verbose:
            self.stdout.write("  [4/5] Checking mount path accessibility...")

        if litefs_settings is not None:
            try:
                detector = PrimaryDetector(litefs_settings.mount_path)
                if verbose:
                    self.stdout.write(
                        f"        OK - Mount path accessible ({litefs_settings.mount_path})"
                    )
            except Exception as e:
                issues.append(
                    ConfigIssue(
                        description=f"Cannot access LiteFS mount path: {e}",
                        fix=f"Ensure mount path '{litefs_settings.mount_path}' exists and is accessible.",
                    )
                )

        return issues, litefs_settings, detector

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute health checks.

        Performs the following checks:
        1. LiteFS configuration is valid and complete
        2. Database backend is litefs_django
        3. LiteFS is enabled
        4. LiteFS mount path is accessible and mounted
        5. Current node role can be determined (primary or replica)

        All issues are collected before reporting, allowing users to see
        all configuration problems at once.

        Returns:
            None on success (exit code 0)

        Raises:
            CommandError: If any health check fails (non-zero exit code)
        """
        verbose = options.get("verbose", False)

        # Collect all issues first (checks 1-4)
        issues, litefs_settings, detector = self._collect_issues(verbose)

        # Health Check 5: Determine node role (only if we have a detector)
        role = None
        if detector is not None:
            if verbose:
                self.stdout.write(
                    "  [5/5] Checking node role (verifies LiteFS is running)..."
                )

            try:
                is_primary = detector.is_primary()
                role = "primary" if is_primary else "replica"
                if verbose:
                    self.stdout.write(f"        OK - Node role is {role}")
            except LiteFSNotRunningError as e:
                issues.append(
                    ConfigIssue(
                        description=f"LiteFS is not running or mount path is inaccessible: {e}",
                        fix="Ensure LiteFS is running and the mount path is properly mounted.",
                    )
                )

        # Report all issues if any exist
        if issues:
            error_lines = ["FAIL: Configuration issues found:"]
            for i, issue in enumerate(issues, 1):
                error_lines.append(f"\n{i}. {issue.description}")
                error_lines.append(f"   Fix: {issue.fix}")
            raise CommandError("".join(error_lines))

        # All checks passed
        if verbose:
            self.stdout.write(self.style.SUCCESS("All health checks passed!"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"LiteFS health check passed (node: {role})")
            )
