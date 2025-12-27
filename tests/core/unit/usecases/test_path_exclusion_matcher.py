"""Unit tests for PathExclusionMatcher use case."""

import pytest
import re

from litefs.usecases.path_exclusion_matcher import PathExclusionMatcher
from litefs.domain.settings import ForwardingSettings


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.PathExclusionMatcher")
class TestPathExclusionMatcher:
    """Test PathExclusionMatcher use case."""

    def test_matches_exact_path(self) -> None:
        """Test matching an exact path pattern."""
        matcher = PathExclusionMatcher(excluded_paths=("/health", "/status"))
        assert matcher.is_excluded("/health") is True
        assert matcher.is_excluded("/status") is True

    def test_no_match_returns_false(self) -> None:
        """Test that non-matching paths return False."""
        matcher = PathExclusionMatcher(excluded_paths=("/health", "/status"))
        assert matcher.is_excluded("/api/users") is False
        assert matcher.is_excluded("/admin") is False

    def test_empty_patterns_never_matches(self) -> None:
        """Test that empty patterns list never matches any path."""
        matcher = PathExclusionMatcher(excluded_paths=())
        assert matcher.is_excluded("/health") is False
        assert matcher.is_excluded("/any/path") is False
        assert matcher.is_excluded("") is False

    def test_matches_glob_pattern_single_wildcard(self) -> None:
        """Test matching glob pattern with single wildcard.

        Note: fnmatch's * matches any characters including /, so
        /api/*/health matches /api/v1/v2/health as well.
        Use regex patterns for stricter segment matching.
        """
        matcher = PathExclusionMatcher(excluded_paths=("/api/*/health",))
        assert matcher.is_excluded("/api/v1/health") is True
        assert matcher.is_excluded("/api/v2/health") is True
        assert matcher.is_excluded("/api/health") is False
        # fnmatch * matches across path segments
        assert matcher.is_excluded("/api/v1/v2/health") is True

    def test_matches_glob_pattern_double_wildcard(self) -> None:
        """Test matching glob pattern with double wildcard (**)."""
        matcher = PathExclusionMatcher(excluded_paths=("/static/**",))
        assert matcher.is_excluded("/static/css/style.css") is True
        assert matcher.is_excluded("/static/js/app.js") is True
        assert matcher.is_excluded("/static/") is True
        assert matcher.is_excluded("/static") is True

    def test_matches_glob_pattern_extension(self) -> None:
        """Test matching glob pattern for file extensions."""
        matcher = PathExclusionMatcher(excluded_paths=("*.css", "*.js"))
        assert matcher.is_excluded("/static/style.css") is True
        assert matcher.is_excluded("/js/app.js") is True
        assert matcher.is_excluded("/style.html") is False

    def test_matches_regex_pattern(self) -> None:
        """Test matching regex pattern (prefixed with 're:')."""
        matcher = PathExclusionMatcher(
            excluded_paths=("re:^/api/v[0-9]+/health$",)
        )
        assert matcher.is_excluded("/api/v1/health") is True
        assert matcher.is_excluded("/api/v2/health") is True
        assert matcher.is_excluded("/api/v10/health") is True
        assert matcher.is_excluded("/api/vX/health") is False
        assert matcher.is_excluded("/api/v1/healthz") is False

    def test_matches_regex_pattern_complex(self) -> None:
        """Test matching complex regex patterns."""
        matcher = PathExclusionMatcher(
            excluded_paths=("re:^/users/\\d+/profile$",)
        )
        assert matcher.is_excluded("/users/123/profile") is True
        assert matcher.is_excluded("/users/1/profile") is True
        assert matcher.is_excluded("/users/abc/profile") is False
        assert matcher.is_excluded("/users/123/settings") is False

    def test_mixed_glob_and_regex_patterns(self) -> None:
        """Test matching with both glob and regex patterns."""
        matcher = PathExclusionMatcher(
            excluded_paths=(
                "/health",
                "/static/*",
                "re:^/api/v[0-9]+/status$",
            )
        )
        assert matcher.is_excluded("/health") is True
        assert matcher.is_excluded("/static/style.css") is True
        assert matcher.is_excluded("/api/v1/status") is True
        assert matcher.is_excluded("/api/users") is False

    def test_integration_with_forwarding_settings(self) -> None:
        """Test creating matcher from ForwardingSettings."""
        settings = ForwardingSettings(
            enabled=True,
            primary_url="http://primary:8000",
            excluded_paths=("/health", "/static/*"),
        )
        matcher = PathExclusionMatcher.from_forwarding_settings(settings)
        assert matcher.is_excluded("/health") is True
        assert matcher.is_excluded("/static/style.css") is True
        assert matcher.is_excluded("/api/users") is False

    def test_from_forwarding_settings_with_empty_paths(self) -> None:
        """Test creating matcher from ForwardingSettings with no exclusions."""
        settings = ForwardingSettings(enabled=True, primary_url="http://primary:8000")
        matcher = PathExclusionMatcher.from_forwarding_settings(settings)
        assert matcher.is_excluded("/health") is False
        assert matcher.is_excluded("/any/path") is False

    def test_invalid_regex_raises_error(self) -> None:
        """Test that invalid regex pattern raises ValueError."""
        with pytest.raises(re.error):
            PathExclusionMatcher(excluded_paths=("re:[invalid",))

    def test_case_sensitive_matching(self) -> None:
        """Test that matching is case-sensitive."""
        matcher = PathExclusionMatcher(excluded_paths=("/Health",))
        assert matcher.is_excluded("/Health") is True
        assert matcher.is_excluded("/health") is False

    def test_query_string_not_included(self) -> None:
        """Test that paths are matched without query strings."""
        matcher = PathExclusionMatcher(excluded_paths=("/health",))
        # The matcher should match the path portion only
        # Caller is responsible for stripping query strings
        assert matcher.is_excluded("/health") is True
        # If query string is included, it won't match exact pattern
        assert matcher.is_excluded("/health?foo=bar") is False

    def test_excluded_paths_property(self) -> None:
        """Test that excluded_paths property returns the patterns."""
        patterns = ("/health", "/static/*")
        matcher = PathExclusionMatcher(excluded_paths=patterns)
        assert matcher.excluded_paths == patterns
