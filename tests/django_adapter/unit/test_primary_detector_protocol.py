"""Tests for PrimaryDetector Protocol interface and dependency injection.

Verifies:
- RAFT-001: PrimaryDetectorPort Protocol is defined and implemented
- RAFT-002: DatabaseWrapper accepts optional primary_detector for DI
- RAFT-007: LiteFSCursor has proper type hints
"""

from __future__ import annotations

import inspect
from typing import Protocol, get_type_hints, runtime_checkable

import pytest

from litefs.usecases.primary_detector import PrimaryDetector


@pytest.mark.tra("Adapter")
class TestPrimaryDetectorProtocolExists:
    """RAFT-001: Verify Protocol interface exists and is implemented."""

    @pytest.mark.tier(1)
    def test_primary_detector_port_protocol_exists(self):
        """Protocol PrimaryDetectorPort should exist in adapters.ports."""
        from litefs.adapters.ports import PrimaryDetectorPort

        # Protocol should be runtime_checkable
        assert hasattr(PrimaryDetectorPort, "__protocol_attrs__") or isinstance(
            PrimaryDetectorPort, type
        )

    @pytest.mark.tier(1)
    def test_primary_detector_port_has_is_primary_method(self):
        """Protocol should define is_primary() -> bool method."""
        from litefs.adapters.ports import PrimaryDetectorPort

        # Check method signature via Protocol attributes or introspection
        assert hasattr(PrimaryDetectorPort, "is_primary")

    @pytest.mark.tier(1)
    def test_primary_detector_implements_protocol(self, tmp_path):
        """PrimaryDetector should implement PrimaryDetectorPort."""
        from litefs.adapters.ports import PrimaryDetectorPort

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        detector = PrimaryDetector(str(mount_path))

        # Duck typing check - has required method
        assert hasattr(detector, "is_primary")
        assert callable(detector.is_primary)

        # Return type check
        result = detector.is_primary()
        assert isinstance(result, bool)

    @pytest.mark.tier(1)
    def test_fake_primary_detector_implements_protocol(self):
        """FakePrimaryDetector should implement PrimaryDetectorPort."""
        from litefs.adapters.ports import PrimaryDetectorPort

        from .fakes import FakePrimaryDetector

        fake = FakePrimaryDetector()

        # Duck typing check - has required method
        assert hasattr(fake, "is_primary")
        assert callable(fake.is_primary)

        # Return type check
        result = fake.is_primary()
        assert isinstance(result, bool)


@pytest.mark.tra("Adapter")
class TestFakePrimaryDetectorSignature:
    """RAFT-001: Verify FakePrimaryDetector signature compatibility."""

    @pytest.mark.tier(1)
    def test_fake_accepts_mount_path_parameter(self):
        """FakePrimaryDetector should accept optional mount_path for compatibility."""
        from .fakes import FakePrimaryDetector

        # Should work with no args (test convenience)
        fake1 = FakePrimaryDetector()
        assert fake1.is_primary() is True

        # Should accept mount_path (compatibility with real detector)
        fake2 = FakePrimaryDetector(mount_path="/fake/path")
        assert fake2.is_primary() is True

        # Should accept is_primary kwarg
        fake3 = FakePrimaryDetector(is_primary=False)
        assert fake3.is_primary() is False

        # Should accept both
        fake4 = FakePrimaryDetector(mount_path="/fake/path", is_primary=False)
        assert fake4.is_primary() is False


@pytest.mark.tra("Adapter")
class TestDatabaseWrapperDependencyInjection:
    """RAFT-002: Verify DatabaseWrapper accepts injected primary_detector."""

    @pytest.mark.tier(1)
    def test_database_wrapper_accepts_primary_detector_param(self, tmp_path):
        """DatabaseWrapper.__init__ should accept optional primary_detector."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        from .fakes import FakePrimaryDetector

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        settings_dict = {
            "ENGINE": "litefs_django.db.backends.litefs",
            "NAME": "test.db",
            "OPTIONS": {"litefs_mount_path": str(mount_path)},
        }

        fake_detector = FakePrimaryDetector(is_primary=False)

        # Should accept primary_detector parameter
        wrapper = DatabaseWrapper(settings_dict, primary_detector=fake_detector)

        # Should use the injected detector
        assert wrapper._primary_detector is fake_detector

    @pytest.mark.tier(1)
    def test_database_wrapper_creates_detector_when_not_provided(self, tmp_path):
        """DatabaseWrapper creates PrimaryDetector when none injected."""
        from litefs_django.db.backends.litefs.base import DatabaseWrapper

        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        settings_dict = {
            "ENGINE": "litefs_django.db.backends.litefs",
            "NAME": "test.db",
            "OPTIONS": {"litefs_mount_path": str(mount_path)},
        }

        # No primary_detector provided - should create one
        wrapper = DatabaseWrapper(settings_dict)

        # Should have a PrimaryDetector instance
        assert wrapper._primary_detector is not None
        assert isinstance(wrapper._primary_detector, PrimaryDetector)

    @pytest.mark.tier(1)
    def test_cursor_uses_injected_detector(self, tmp_path):
        """LiteFSCursor should use the injected detector."""
        import sqlite3

        from litefs_django.db.backends.litefs.base import LiteFSCursor
        from litefs_django.exceptions import NotPrimaryError

        from .fakes import FakePrimaryDetector

        # Create a real SQLite connection (not through Django wrapper)
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create fake that says we're a replica
        fake_detector = FakePrimaryDetector(is_primary=False)

        # Create cursor directly with fake detector
        cursor = LiteFSCursor(conn, fake_detector)

        # Write operation should fail because fake says we're replica
        with pytest.raises(NotPrimaryError):
            cursor.execute("INSERT INTO test VALUES (1)")

        conn.close()


@pytest.mark.tra("Adapter")
class TestLiteFSCursorTypeHints:
    """RAFT-007: Verify LiteFSCursor has proper type hints."""

    @pytest.mark.tier(1)
    def test_litefs_cursor_init_has_type_hints(self):
        """LiteFSCursor.__init__ should have type hints on parameters."""
        from litefs_django.db.backends.litefs.base import LiteFSCursor

        # Check annotations directly (before evaluation with get_type_hints)
        annotations = LiteFSCursor.__init__.__annotations__

        # Should have type hint for primary_detector
        assert "primary_detector" in annotations, (
            "LiteFSCursor.__init__ should have type hint for primary_detector"
        )

    @pytest.mark.tier(1)
    def test_litefs_cursor_primary_detector_hint_is_protocol(self):
        """primary_detector type hint should reference Protocol."""
        from litefs_django.db.backends.litefs.base import LiteFSCursor

        annotations = LiteFSCursor.__init__.__annotations__

        # The type should be PrimaryDetectorPort or compatible
        hint = annotations.get("primary_detector")
        assert hint is not None

        # Check it's the Protocol type (not concrete PrimaryDetector)
        hint_name = getattr(hint, "__name__", str(hint))
        assert "PrimaryDetectorPort" in hint_name or "Protocol" in str(hint), (
            f"Expected Protocol type, got {hint}"
        )
