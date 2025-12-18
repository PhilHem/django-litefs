"""Concurrency tests for Django database backend."""

import threading
from pathlib import Path

import pytest

from litefs.usecases.primary_detector import PrimaryDetector


@pytest.mark.unit
@pytest.mark.concurrency
class TestDatabaseBackendConcurrency:
    """Test concurrency issues in Django database backend."""

    def test_primary_detector_concurrent_access(self, tmp_path):
        """Test that PrimaryDetector handles concurrent is_primary() calls safely.

        This test simulates multiple threads calling is_primary() simultaneously
        during failover scenarios where .primary file is being created/deleted.
        Verifies no exceptions occur and all calls complete successfully.
        """
        mount_path = tmp_path / "litefs"
        mount_path.mkdir()
        primary_file = mount_path / ".primary"

        detector = PrimaryDetector(mount_path=str(mount_path))
        results = []
        errors = []
        lock = threading.Lock()

        def check_primary():
            """Thread function to check primary status."""
            try:
                result = detector.is_primary()
                with lock:
                    results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Simulate failover: create and delete .primary file rapidly
        def toggle_primary():
            """Thread function to toggle primary file."""
            for _ in range(50):
                if primary_file.exists():
                    primary_file.unlink()
                else:
                    primary_file.write_text("node-1")
                # Small delay to allow race conditions
                threading.Event().wait(0.0001)

        # Start threads
        threads = []
        for _ in range(50):
            t = threading.Thread(target=check_primary)
            threads.append(t)
            t.start()

        # Start toggle thread
        toggle_thread = threading.Thread(target=toggle_primary)
        toggle_thread.start()

        # Wait for all threads
        for t in threads:
            t.join()
        toggle_thread.join()

        # Verify no exceptions occurred
        assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"

        # Verify all calls completed (results may vary based on timing)
        assert len(results) == 50, f"Not all threads completed: {len(results)}/50"

    def test_concurrent_connection_initialization(self, tmp_path):
        """Test that concurrent connection initialization doesn't cause contention.

        This test simulates multiple threads calling get_new_connection() simultaneously
        to verify that WAL mode setting doesn't cause issues.
        """
        # This test requires Django setup, so we'll skip it for now and add it
        # when we have proper Django test infrastructure
        pytest.skip(
            "Requires Django test infrastructure - will be added in integration tests"
        )
