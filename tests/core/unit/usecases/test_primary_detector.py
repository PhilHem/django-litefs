"""Unit tests for PrimaryDetector use case."""

import os
import random
import threading
import pytest
from pathlib import Path
from unittest.mock import Mock

from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError


@pytest.mark.unit
class TestPrimaryDetector:
    """Test PrimaryDetector use case."""

    def test_detect_primary_when_file_exists(self, tmp_path):
        """Test detecting primary when .primary file exists."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        detector = PrimaryDetector(mount_path=str(mount_path))
        assert detector.is_primary() is True

    def test_detect_replica_when_file_does_not_exist(self, tmp_path):
        """Test detecting replica when .primary file does not exist."""
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()

        detector = PrimaryDetector(mount_path=str(mount_path))
        assert detector.is_primary() is False

    def test_raise_error_when_mount_path_does_not_exist(self):
        """Test that error is raised when mount path doesn't exist."""
        detector = PrimaryDetector(mount_path="/nonexistent/path")
        with pytest.raises(LiteFSNotRunningError):
            detector.is_primary()


@pytest.mark.unit
@pytest.mark.concurrency
class TestPrimaryDetectorConcurrency:
    """Test concurrency issues in PrimaryDetector."""

    def test_mount_path_deletion_during_check(self, tmp_path):
        """Test CORE-002: Mount path deletion race condition.

        Multiple threads call is_primary() while mount_path is deleted/recreated
        concurrently. Verifies that all calls either raise LiteFSNotRunningError
        or return boolean (no inconsistent state).
        """
        base_path = tmp_path / "base"
        base_path.mkdir()
        mount_path = base_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        detector = PrimaryDetector(mount_path=str(mount_path))
        results = []
        errors = []
        lock = threading.Lock()

        def check_primary():
            """Thread function to check primary status."""
            try:
                result = detector.is_primary()
                with lock:
                    results.append(("success", result))
            except LiteFSNotRunningError as e:
                with lock:
                    errors.append(("LiteFSNotRunningError", str(e)))
            except Exception as e:
                with lock:
                    errors.append((type(e).__name__, str(e)))

        def toggle_mount_path():
            """Thread function to delete/recreate mount_path."""
            for _ in range(100):
                if mount_path.exists():
                    # Delete mount_path (and its contents)
                    import shutil

                    shutil.rmtree(mount_path)
                else:
                    # Recreate mount_path
                    mount_path.mkdir()
                    if random.random() < 0.5:  # Randomly create .primary file
                        (mount_path / ".primary").write_text("node-1")
                # Small delay to allow race conditions
                threading.Event().wait(0.001)

        # Start threads
        threads = []
        for _ in range(50):
            t = threading.Thread(target=check_primary)
            threads.append(t)
            t.start()

        # Start toggle thread
        toggle_thread = threading.Thread(target=toggle_mount_path)
        toggle_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        toggle_thread.join()

        # Verify: All calls completed (either success or LiteFSNotRunningError)
        total_calls = len(results) + len(errors)
        assert total_calls == 50, f"Not all threads completed: {total_calls}/50"

        # Verify: All exceptions are LiteFSNotRunningError (no other exception types)
        exception_types = [err_type for err_type, _ in errors]
        non_expected_errors = [
            err for err_type, err_msg in errors if err_type != "LiteFSNotRunningError"
        ]
        assert len(non_expected_errors) == 0, (
            f"Unexpected exception types during mount path deletion: {non_expected_errors}. "
            f"All exceptions should be LiteFSNotRunningError, but got: {set(exception_types)}"
        )

        # Verify: Results are consistent (all booleans)
        for result_type, value in results:
            assert isinstance(value, bool), (
                f"Expected boolean result, got {type(value)}"
            )

    def test_symlink_change_during_detector_lifetime(self, tmp_path):
        """Test CORE-013: Symlink staleness issue.

        Create detector with symlink path, change symlink target, verify detector
        uses updated path (resolves symlink on each call, not cached).
        """
        # Create two target directories
        target1 = tmp_path / "target1"
        target2 = tmp_path / "target2"
        target1.mkdir()
        target2.mkdir()

        # Create symlink pointing to target1
        symlink_path = tmp_path / "litefs_symlink"
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(target1)

        # Create .primary file in target1
        (target1 / ".primary").write_text("node-1")

        # Create detector with symlink path
        detector = PrimaryDetector(mount_path=str(symlink_path))

        # Verify detector sees .primary file initially
        assert detector.is_primary() is True

        # Change symlink to point to target2 (which has no .primary file)
        symlink_path.unlink()
        symlink_path.symlink_to(target2)

        # Verify detector now sees updated symlink (should return False)
        # This tests that detector resolves symlink on each call, not cached
        assert detector.is_primary() is False, (
            "Detector should resolve symlink on each call. "
            "If this fails, detector is using cached/stale path reference."
        )

        # Change symlink back to target1
        symlink_path.unlink()
        symlink_path.symlink_to(target1)

        # Verify detector sees .primary file again
        assert detector.is_primary() is True, (
            "Detector should resolve updated symlink. "
            "If this fails, detector is not resolving symlink on each call."
        )

    def test_exception_type_consistency_during_deletion(self, tmp_path):
        """Test CORE-014: Exception type consistency during concurrent deletion.

        Multiple threads call is_primary() while mount_path is deleted at various
        timing points. Verifies that all exceptions are LiteFSNotRunningError
        (not OSError or other types) regardless of deletion timing.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"
        primary_file.write_text("node-1")

        detector = PrimaryDetector(mount_path=str(mount_path))
        results = []
        errors = []
        lock = threading.Lock()

        def check_primary():
            """Thread function to check primary status."""
            try:
                result = detector.is_primary()
                with lock:
                    results.append(("success", result))
            except LiteFSNotRunningError as e:
                with lock:
                    errors.append(("LiteFSNotRunningError", str(e)))
            except OSError as e:
                with lock:
                    errors.append(("OSError", str(e)))
            except Exception as e:
                with lock:
                    errors.append((type(e).__name__, str(e)))

        def delete_mount_path():
            """Thread function to delete mount_path at various timing points."""
            for _ in range(200):
                if mount_path.exists():
                    import shutil

                    shutil.rmtree(mount_path)
                else:
                    mount_path.mkdir()
                    if random.random() < 0.3:  # Randomly create .primary file
                        (mount_path / ".primary").write_text("node-1")
                # Variable delay to create different timing scenarios
                threading.Event().wait(random.uniform(0.0001, 0.002))

        # Start threads
        threads = []
        for _ in range(100):
            t = threading.Thread(target=check_primary)
            threads.append(t)
            t.start()

        # Start deletion thread
        delete_thread = threading.Thread(target=delete_mount_path)
        delete_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        delete_thread.join()

        # Verify: All calls completed
        total_calls = len(results) + len(errors)
        assert total_calls == 100, f"Not all threads completed: {total_calls}/100"

        # Verify: All exceptions are LiteFSNotRunningError (not OSError or others)
        exception_types = [err_type for err_type, _ in errors]
        unexpected_errors = [
            (err_type, err_msg)
            for err_type, err_msg in errors
            if err_type != "LiteFSNotRunningError"
        ]
        assert len(unexpected_errors) == 0, (
            f"Exception type inconsistency detected: {unexpected_errors}. "
            f"All exceptions should be LiteFSNotRunningError, but got: {set(exception_types)}. "
            f"This indicates exception type varies based on timing of deletion relative to "
            f"mount_path.exists() vs primary_file.exists() checks."
        )
