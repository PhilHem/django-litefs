"""Django management command for LiteFS health checks."""

import json
from dataclasses import dataclass, asdict
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


@dataclass
class CheckResult:
    """Result of a single health check."""

    name: str
    passed: bool
    message: str | None = None


class Command(BaseCommand):
    """Perform health checks suitable for deployment readiness."""

    help = "Perform LiteFS health checks for deployment readiness (exit 0 on success, non-zero on failure)"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            help="Show detailed health check results (deprecated, use -v 2)",
        )
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            dest="format",
            help="Output format: text (default) or json",
        )

    def _collect_issues(
        self, verbosity: int
    ) -> tuple[
        list[ConfigIssue],
        list[CheckResult],
        "LiteFSSettings | None",
        "PrimaryDetector | None",
    ]:
        """Collect all configuration issues without failing fast.

        Returns:
            Tuple of (issues list, check results, settings if valid, detector if created)
        """
        issues: list[ConfigIssue] = []
        checks: list[CheckResult] = []
        litefs_settings = None
        detector = None

        # Health Check 1: Validate configuration
        if verbosity >= 2:
            self.stdout.write("Performing health checks...")
            self.stdout.write("  [1/5] Validating LiteFS configuration...")

        try:
            django_settings = getattr(settings, "LITEFS", {})
            litefs_settings = get_litefs_settings(django_settings)
            checks.append(CheckResult(name="config", passed=True, message="Valid"))
        except LiteFSConfigError as e:
            issues.append(
                ConfigIssue(
                    description=f"Invalid LiteFS configuration: {e}",
                    fix="Check your LITEFS settings dict in Django settings.",
                )
            )
            checks.append(CheckResult(name="config", passed=False, message=str(e)))

        # Health Check 2: Validate database backend
        if verbosity >= 2:
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
            checks.append(
                CheckResult(
                    name="database_backend",
                    passed=False,
                    message=f"Expected {expected_backend}, got {actual_backend}",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="database_backend", passed=True, message=expected_backend
                )
            )
            if verbosity >= 2:
                self.stdout.write(f"        OK - Database backend is {expected_backend}")

        # Health Check 3: Verify LiteFS is enabled
        if verbosity >= 2:
            self.stdout.write("  [3/5] Checking if LiteFS is enabled...")

        if litefs_settings is not None and not litefs_settings.enabled:
            issues.append(
                ConfigIssue(
                    description="LiteFS is disabled (LITEFS.ENABLED=False).",
                    fix="Enable LiteFS before deployment by setting LITEFS['ENABLED'] = True.",
                )
            )
            checks.append(
                CheckResult(name="enabled", passed=False, message="LiteFS is disabled")
            )
        elif litefs_settings is not None:
            checks.append(CheckResult(name="enabled", passed=True, message="Enabled"))
            if verbosity >= 2:
                self.stdout.write("        OK - LiteFS is enabled")

        # Health Check 4: Verify mount path is accessible
        if verbosity >= 2:
            self.stdout.write("  [4/5] Checking mount path accessibility...")

        if litefs_settings is not None:
            try:
                detector = PrimaryDetector(litefs_settings.mount_path)
                checks.append(
                    CheckResult(
                        name="mount_path",
                        passed=True,
                        message=str(litefs_settings.mount_path),
                    )
                )
                if verbosity >= 2:
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
                checks.append(
                    CheckResult(name="mount_path", passed=False, message=str(e))
                )

        return issues, checks, litefs_settings, detector

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
        verbosity = options.get("verbosity", 1)
        verbose_flag = options.get("verbose", False)
        output_format = options.get("format", "text")

        # --verbose flag is equivalent to verbosity >= 2
        if verbose_flag:
            verbosity = max(verbosity, 2)

        # Collect all issues first (checks 1-4)
        issues, checks, litefs_settings, detector = self._collect_issues(verbosity)

        # Health Check 5: Determine node role (only if we have a detector)
        role = None
        if detector is not None:
            if verbosity >= 2:
                self.stdout.write(
                    "  [5/5] Checking node role (verifies LiteFS is running)..."
                )

            try:
                is_primary = detector.is_primary()
                role = "primary" if is_primary else "replica"
                checks.append(CheckResult(name="node_role", passed=True, message=role))
                if verbosity >= 2:
                    self.stdout.write(f"        OK - Node role is {role}")
            except LiteFSNotRunningError as e:
                issues.append(
                    ConfigIssue(
                        description=f"LiteFS is not running or mount path is inaccessible: {e}",
                        fix="Ensure LiteFS is running and the mount path is properly mounted.",
                    )
                )
                checks.append(
                    CheckResult(name="node_role", passed=False, message=str(e))
                )

        # Handle JSON output
        if output_format == "json":
            if issues:
                data = {
                    "status": "error",
                    "checks": [asdict(c) for c in checks],
                    "issues": [
                        {"description": i.description, "fix": i.fix} for i in issues
                    ],
                }
                self.stdout.write(json.dumps(data, indent=2))
                raise CommandError("Health checks failed")
            else:
                data = {
                    "status": "ok",
                    "checks": [asdict(c) for c in checks],
                    "role": role,
                }
                self.stdout.write(json.dumps(data, indent=2))
                return

        # Text output: Report all issues if any exist
        if issues:
            error_lines = ["FAIL: Configuration issues found:"]
            for i, issue in enumerate(issues, 1):
                error_lines.append(f"\n{i}. {issue.description}")
                error_lines.append(f"   Fix: {issue.fix}")
            raise CommandError("".join(error_lines))

        # All checks passed
        if verbosity == 0:
            # Silent mode - no output on success
            return
        elif verbosity >= 2:
            self.stdout.write(self.style.SUCCESS("All health checks passed!"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"LiteFS health check passed (node: {role})")
            )
