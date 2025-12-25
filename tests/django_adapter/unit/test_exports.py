"""Unit tests for litefs_django public API exports."""

import pytest


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestPublicAPIExports:
    """Test that the public API exports are correctly defined."""

    def test_exports_all_required_classes(self):
        """Verify all required items are exported in __all__."""
        import litefs_django

        expected_exports = {
            "LiteFSDjangoConfig",
            "NotPrimaryError",
            "SplitBrainError",
            "get_litefs_settings",
            "split_brain_detected",
        }
        assert set(litefs_django.__all__) == expected_exports

    def test_all_exports_are_strings(self):
        """Verify that __all__ contains only strings."""
        import litefs_django

        assert isinstance(litefs_django.__all__, list)
        assert all(isinstance(item, str) for item in litefs_django.__all__)

    def test_litefs_django_config_exportable(self):
        """Test that LiteFSDjangoConfig can be imported from litefs_django."""
        from litefs_django import LiteFSDjangoConfig

        assert LiteFSDjangoConfig is not None
        assert hasattr(LiteFSDjangoConfig, "ready")

    def test_not_primary_error_exportable(self):
        """Test that NotPrimaryError can be imported from litefs_django."""
        from litefs_django import NotPrimaryError

        assert NotPrimaryError is not None
        assert issubclass(NotPrimaryError, Exception)

    def test_split_brain_error_exportable(self):
        """Test that SplitBrainError can be imported from litefs_django."""
        from litefs_django import SplitBrainError

        assert SplitBrainError is not None
        assert issubclass(SplitBrainError, Exception)

    def test_get_litefs_settings_exportable(self):
        """Test that get_litefs_settings can be imported from litefs_django."""
        from litefs_django import get_litefs_settings

        assert get_litefs_settings is not None
        assert callable(get_litefs_settings)

    def test_split_brain_detected_signal_still_exported(self):
        """Test that split_brain_detected signal remains exported."""
        from litefs_django import split_brain_detected

        assert split_brain_detected is not None
        # Django signals are instances of django.dispatch.Signal
        assert hasattr(split_brain_detected, "send")

    def test_version_exists(self):
        """Test that __version__ is defined."""
        import litefs_django

        assert hasattr(litefs_django, "__version__")
        assert isinstance(litefs_django.__version__, str)

    def test_no_unexpected_exports(self):
        """Test that only intended items are in __all__."""
        import litefs_django

        # Verify no extra items beyond what we expect
        for item in litefs_django.__all__:
            assert hasattr(litefs_django, item), (
                f"Item '{item}' is in __all__ but not defined in module"
            )
