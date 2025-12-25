"""Contract tests for FakePrimaryDetector.

These tests verify that FakePrimaryDetector implements the same interface
as the real PrimaryDetector, ensuring test fakes behave correctly.
"""

import sqlite3

import pytest

from litefs.usecases.primary_detector import LiteFSNotRunningError, PrimaryDetector

from .fakes import FakePrimaryDetector


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter")
class TestFakePrimaryDetectorContract:
    """Verify FakePrimaryDetector implements same interface as real."""

    def test_fake_primary_detector_default_is_primary(self, fake_primary_detector):
        """Test default state is primary."""
        assert fake_primary_detector.is_primary() is True

    def test_fake_primary_detector_set_replica(self, fake_primary_detector):
        """Test can set to replica state."""
        fake_primary_detector.set_primary(False)
        assert fake_primary_detector.is_primary() is False

    def test_fake_primary_detector_toggle_state(self, fake_primary_detector):
        """Test can toggle between states."""
        assert fake_primary_detector.is_primary() is True
        fake_primary_detector.set_primary(False)
        assert fake_primary_detector.is_primary() is False
        fake_primary_detector.set_primary(True)
        assert fake_primary_detector.is_primary() is True

    def test_fake_primary_detector_error_injection(self, fake_primary_detector):
        """Test can inject LiteFSNotRunningError."""
        fake_primary_detector.set_error(LiteFSNotRunningError("Mount path missing"))
        with pytest.raises(LiteFSNotRunningError):
            fake_primary_detector.is_primary()

    def test_fake_primary_detector_clear_error(self, fake_primary_detector):
        """Test can clear error after injection."""
        fake_primary_detector.set_error(LiteFSNotRunningError("Test error"))
        with pytest.raises(LiteFSNotRunningError):
            fake_primary_detector.is_primary()

        # Clear error
        fake_primary_detector.set_error(None)
        assert fake_primary_detector.is_primary() is True

    def test_fake_vs_real_primary_detector_interface(self, tmp_path):
        """Differential test: Fake implements same interface as Real."""
        # Real detector
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        real = PrimaryDetector(str(mount_path))

        # Fake detector
        fake = FakePrimaryDetector(is_primary=False)

        # Both have is_primary method returning bool
        assert isinstance(real.is_primary(), bool)
        assert isinstance(fake.is_primary(), bool)

        # Both can return True when primary
        (mount_path / ".primary").write_text("node-1")
        fake.set_primary(True)
        assert real.is_primary() is True
        assert fake.is_primary() is True

        # Both can return False when replica
        (mount_path / ".primary").unlink()
        fake.set_primary(False)
        assert real.is_primary() is False
        assert fake.is_primary() is False

    def test_cursor_with_fake_primary_detector(self, tmp_path, fake_primary_detector):
        """Test LiteFSCursor works with FakePrimaryDetector."""
        from litefs_django.db.backends.litefs.base import LiteFSCursor
        from litefs_django.exceptions import NotPrimaryError

        # Create real SQLite connection
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")

        # Use FakePrimaryDetector with real cursor
        cursor = LiteFSCursor(conn, fake_primary_detector)

        # Should work when primary
        fake_primary_detector.set_primary(True)
        cursor.execute("INSERT INTO test VALUES (1)")

        # Should fail when replica
        fake_primary_detector.set_primary(False)
        with pytest.raises(NotPrimaryError):
            cursor.execute("INSERT INTO test VALUES (2)")

        conn.close()

    def test_fake_primary_detector_initial_replica_state(self):
        """Test can initialize with replica state."""
        fake = FakePrimaryDetector(is_primary=False)
        assert fake.is_primary() is False
