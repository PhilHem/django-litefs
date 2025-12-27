"""Path exclusion matcher use case for write forwarding."""

from __future__ import annotations

import fnmatch
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litefs.domain.settings import ForwardingSettings


class PathExclusionMatcher:
    """Matches request paths against configured exclusion patterns.

    Supports both glob patterns (using fnmatch) and regex patterns.
    Regex patterns must be prefixed with 're:' to be recognized.

    Examples:
        - '/health' - exact path match
        - '/static/*' - glob pattern matching one path segment
        - '/static/**' - glob pattern matching multiple path segments
        - '*.css' - glob pattern matching file extension
        - 're:^/api/v[0-9]+/health$' - regex pattern

    Attributes:
        excluded_paths: Tuple of path patterns to check against.
    """

    REGEX_PREFIX = "re:"

    def __init__(self, excluded_paths: tuple[str, ...]) -> None:
        """Initialize the path exclusion matcher.

        Args:
            excluded_paths: Tuple of path patterns to exclude.
                           Patterns prefixed with 're:' are treated as regex.
                           All other patterns are treated as glob patterns.

        Raises:
            re.error: If a regex pattern is invalid.
        """
        self._excluded_paths = excluded_paths
        self._compiled_patterns: list[tuple[str, re.Pattern[str] | None]] = []

        for pattern in excluded_paths:
            if pattern.startswith(self.REGEX_PREFIX):
                regex_str = pattern[len(self.REGEX_PREFIX) :]
                compiled = re.compile(regex_str)
                self._compiled_patterns.append((pattern, compiled))
            else:
                self._compiled_patterns.append((pattern, None))

    @property
    def excluded_paths(self) -> tuple[str, ...]:
        """Return the configured exclusion patterns."""
        return self._excluded_paths

    def is_excluded(self, path: str) -> bool:
        """Check if a path should be excluded from forwarding.

        Args:
            path: The request path to check (without query string).

        Returns:
            True if the path matches any exclusion pattern, False otherwise.
        """
        for pattern, compiled_regex in self._compiled_patterns:
            if compiled_regex is not None:
                # Regex pattern
                if compiled_regex.match(path):
                    return True
            else:
                # Glob pattern - handle ** for recursive matching
                if "**" in pattern:
                    # Convert ** to match anything including /
                    glob_pattern = pattern.replace("**", "*")
                    # For ** patterns, we need to match the path or path + anything
                    if fnmatch.fnmatch(path, glob_pattern):
                        return True
                    # Also try matching with the original path stripped of the pattern base
                    base = pattern.split("**")[0].rstrip("/")
                    if path.startswith(base):
                        return True
                elif fnmatch.fnmatch(path, pattern):
                    return True

        return False

    @classmethod
    def from_forwarding_settings(
        cls, settings: ForwardingSettings
    ) -> PathExclusionMatcher:
        """Create a PathExclusionMatcher from ForwardingSettings.

        Args:
            settings: The forwarding settings containing excluded_paths.

        Returns:
            A PathExclusionMatcher configured with the settings' excluded paths.
        """
        return cls(excluded_paths=settings.excluded_paths)
