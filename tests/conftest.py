"""
Root conftest.py for django-litefs test suite.

Pytest plugin that enforces TRA (Test Responsibility Architecture) and Tier markers.
- Fails collection if test missing TRA marker or tier marker
- Enforces tier timeouts
- Currently uses enforcement='warn' during migration (no collection failures)

Installation:
    This file is automatically discovered by pytest.

Usage:
    @pytest.mark.tier(1)
    @pytest.mark.tra("Domain.Invariant.OrderMustHaveItems")
    def test_something():
        ...

Configuration:
    Set TIER_ENFORCE=0 to disable tier enforcement during migration
    Set TRA_ENFORCE=0 to disable TRA enforcement during migration
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Item


# ============================================================================
# TRA (Test Responsibility Architecture) Configuration
# ============================================================================

# Valid TRA namespace prefixes
VALID_TRA_PREFIXES = frozenset(
    [
        "Domain.Invariant.",
        "Domain.Policy.",
        "UseCase.",
        "Port.",
        "Adapter.",
        "Contract.",
    ]
)


# ============================================================================
# Tier Configuration
# ============================================================================

# Tier timeout limits in seconds
TIER_TIMEOUTS: dict[int, float] = {
    0: 0.1,  # 100ms - instant
    1: 2.0,  # 2s - fast (pre-commit)
    2: 30.0,  # 30s - standard (CI)
    3: 300.0,  # 5min - slow (merge to main)
    4: 0,  # No limit - manual
}

# Tier names for error messages
TIER_NAMES: dict[int, str] = {
    0: "instant",
    1: "fast",
    2: "standard",
    3: "slow",
    4: "manual",
}


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(config: Config) -> None:
    """Register custom markers for TRA and Tier enforcement."""
    config.addinivalue_line(
        "markers",
        "tra(anchor): Test Responsibility Anchor - declares the single responsibility this test protects. "
        "Must start with one of: Domain.Invariant, Domain.Policy, UseCase, Port, Adapter, Contract",
    )
    config.addinivalue_line(
        "markers",
        "tier(level): Test tier (0=instant, 1=fast, 2=standard, 3=slow, 4=manual). "
        "Determines when test runs and enforces timeout.",
    )
    config.addinivalue_line(
        "markers",
        "legacy: Marks test as legacy (no TRA yet). Must be migrated, never add new ones.",
    )
    # DEPRECATED markers - kept for backwards compatibility during migration
    config.addinivalue_line(
        "markers",
        "unit: DEPRECATED - use tier(1) instead. Unit tests (fast, no LiteFS process)",
    )
    config.addinivalue_line(
        "markers",
        "integration: DEPRECATED - use tier(3) instead. Integration tests (requires Docker + FUSE)",
    )
    config.addinivalue_line(
        "markers", "property: Property-based tests using Hypothesis"
    )
    config.addinivalue_line(
        "markers", "concurrency: DEPRECATED - use tier(2) instead. Concurrency tests"
    )
    config.addinivalue_line(
        "markers",
        "no_parallel: Tests that cannot run in parallel (shared state/filesystem)",
    )


def _get_tier(item: Item) -> int | None:
    """Extract tier level from item's markers."""
    for marker in item.iter_markers(name="tier"):
        if marker.args:
            tier = marker.args[0]
            if isinstance(tier, int) and 0 <= tier <= 4:
                return tier
    return None


def _enforce_tra_markers(items: list[Item]) -> list[str]:
    """
    Validate TRA markers on all tests.

    Returns:
        List of error messages. Empty if all valid.
    """
    enforce_mode = os.environ.get("TRA_ENFORCE", "warn")
    if enforce_mode == "0":
        return []

    errors = []

    for item in items:
        tra_markers = list(item.iter_markers(name="tra"))
        legacy_markers = list(item.iter_markers(name="legacy"))

        test_id = item.nodeid

        # Rule: Cannot have both @tra and @legacy
        if tra_markers and legacy_markers:
            errors.append(f"{test_id}: Cannot have both @tra and @legacy markers")
            continue

        # Rule: Must have exactly one of @tra or @legacy
        if not tra_markers and not legacy_markers:
            errors.append(
                f"{test_id}: Missing @pytest.mark.tra('...') or @pytest.mark.legacy"
            )
            continue

        # Rule: Exactly one @tra marker
        if len(tra_markers) > 1:
            errors.append(
                f"{test_id}: Multiple @tra markers found. Each test must have exactly one responsibility."
            )
            continue

        if tra_markers:
            marker = tra_markers[0]

            # Rule: @tra must have an argument
            if not marker.args:
                errors.append(f"{test_id}: @tra marker missing anchor argument")
                continue

            anchor = marker.args[0]

            # Rule: Anchor must be a non-empty string
            if not isinstance(anchor, str) or not anchor.strip():
                errors.append(f"{test_id}: @tra anchor must be a non-empty string")
                continue

            # Rule: Anchor must follow canonical namespace
            if not any(anchor.startswith(prefix) for prefix in VALID_TRA_PREFIXES):
                valid = ", ".join(sorted(VALID_TRA_PREFIXES))
                errors.append(
                    f"{test_id}: Invalid TRA anchor '{anchor}'. Must start with one of: {valid}"
                )
                continue

    return errors


def _enforce_tier_markers(items: list[Item]) -> list[str]:
    """
    Validate tier markers on all tests.

    Returns:
        List of error messages. Empty if all valid.
    """
    enforce_mode = os.environ.get("TIER_ENFORCE", "warn")
    if enforce_mode == "0":
        return []

    errors = []
    missing: list[str] = []
    invalid: list[str] = []

    for item in items:
        tier_markers = list(item.iter_markers(name="tier"))

        if not tier_markers:
            missing.append(item.nodeid)
        elif len(tier_markers) > 1:
            invalid.append(f"{item.nodeid} (multiple tier markers)")
        else:
            tier = _get_tier(item)
            if tier is None:
                invalid.append(f"{item.nodeid} (invalid tier value)")

    if missing:
        errors.append(
            f"\nTests missing @pytest.mark.tier() marker ({len(missing)}):\n"
            + "\n".join(f"  - {nodeid}" for nodeid in missing[:10])
        )
        if len(missing) > 10:
            errors.append(f"  ... and {len(missing) - 10} more")

    if invalid:
        errors.append(
            f"\nTests with invalid tier markers ({len(invalid)}):\n"
            + "\n".join(f"  - {msg}" for msg in invalid[:10])
        )

    return errors


def _apply_tier_timeouts(items: list[Item], config: Config) -> None:
    """Apply timeout based on tier level.

    Only applies if pytest-timeout is installed and no explicit timeout is set.
    Respects TIER_TIMEOUT_MULTIPLIER environment variable.
    """
    try:
        import pytest_timeout as _  # type: ignore[import-untyped]  # noqa: F401
    except ImportError:
        # pytest-timeout not installed, skip
        return

    multiplier = float(os.environ.get("TIER_TIMEOUT_MULTIPLIER", "1.0"))

    for item in items:
        tier = _get_tier(item)
        if tier is None:
            continue

        # Skip if explicit timeout marker exists
        if any(item.iter_markers(name="timeout")):
            continue

        timeout = TIER_TIMEOUTS.get(tier, 0)
        if timeout > 0:
            adjusted_timeout = timeout * multiplier
            # Add timeout marker dynamically
            item.add_marker(pytest.mark.timeout(adjusted_timeout))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """
    Enforce TRA and Tier markers at collection time.

    Currently uses enforcement='warn' mode - warns but doesn't fail collection.
    """
    tra_errors = _enforce_tra_markers(items)
    tier_errors = _enforce_tier_markers(items)

    # Collect all errors
    all_errors = tra_errors + tier_errors

    if all_errors:
        enforce_mode = os.environ.get("TRA_ENFORCE", "warn")
        tier_enforce_mode = os.environ.get("TIER_ENFORCE", "warn")

        # During migration (enforce='warn'), show warnings but don't fail
        if enforce_mode == "warn" or tier_enforce_mode == "warn":
            print("\nTRA/Tier Enforcement Warnings (migration mode):")
            for error in all_errors:
                print(f"  {error}")
        else:
            # Strict mode (enforce='1' or unset): fail collection
            error_msg = "TRA/Tier Enforcement Errors:\n" + "\n".join(
                f"  - {e}" for e in all_errors
            )
            pytest.fail(error_msg, pytrace=False)

    # Apply tier-based timeouts
    _apply_tier_timeouts(items, config)


# ============================================================================
# Reporting
# ============================================================================


class EnforcementStats:
    """Collect enforcement statistics for reporting."""

    def __init__(self) -> None:
        self.total: int = 0
        self.with_tra: int = 0
        self.legacy: int = 0
        self.with_tier: int = 0
        self.by_namespace: dict[str, int] = {}
        self.by_tier: dict[int, int] = {}

    def record(self, item: Item) -> None:
        self.total += 1
        tra_markers = list(item.iter_markers(name="tra"))
        legacy_markers = list(item.iter_markers(name="legacy"))
        tier = _get_tier(item)

        if legacy_markers:
            self.legacy += 1
        elif tra_markers:
            self.with_tra += 1
            anchor = tra_markers[0].args[0]
            namespace = anchor.split(".")[0]
            self.by_namespace[namespace] = self.by_namespace.get(namespace, 0) + 1

        if tier is not None:
            self.with_tier += 1
            self.by_tier[tier] = self.by_tier.get(tier, 0) + 1


@pytest.hookimpl(trylast=True)
def pytest_report_header(config: Config) -> str:
    """Add enforcement info to pytest header."""
    tra_enforce = os.environ.get("TRA_ENFORCE", "warn")
    tier_enforce = os.environ.get("TIER_ENFORCE", "warn")
    return f"TRA enforcement: {tra_enforce} | Tier enforcement: {tier_enforce}"


def pytest_terminal_summary(
    terminalreporter: object, exitstatus: int, config: Config
) -> None:
    """Print enforcement summary at end of test run."""
    stats = EnforcementStats()

    # Type narrowing: access stats attribute dynamically
    if hasattr(terminalreporter, "stats") and hasattr(terminalreporter, "write_line"):
        stats_dict = getattr(terminalreporter, "stats", {})
        for item in stats_dict.get("passed", []):
            if hasattr(item, "item") and hasattr(item.item, "iter_markers"):
                stats.record(item.item)
        for item in stats_dict.get("failed", []):
            if hasattr(item, "item") and hasattr(item.item, "iter_markers"):
                stats.record(item.item)

        if stats.total > 0:
            write_sep = getattr(terminalreporter, "write_sep")
            write_line = getattr(terminalreporter, "write_line")

            write_sep("=", "TRA/Tier Enforcement Summary")
            write_line(f"  Total tests: {stats.total}")
            write_line(f"  TRA anchored: {stats.with_tra}")
            write_line(f"  Legacy tests: {stats.legacy}")
            write_line(f"  With tier: {stats.with_tier}")

            if stats.legacy > 0:
                pct = (stats.legacy / stats.total) * 100
                write_line(f"  Legacy debt: {pct:.1f}%")

            if stats.by_namespace:
                write_line("  By TRA namespace:")
                for ns, count in sorted(stats.by_namespace.items()):
                    write_line(f"    {ns}: {count}")

            if stats.by_tier:
                write_line("  By tier:")
                for tier in sorted(stats.by_tier.keys()):
                    count = stats.by_tier[tier]
                    name = TIER_NAMES.get(tier, "unknown")
                    write_line(f"    tier({tier}) [{name}]: {count}")
