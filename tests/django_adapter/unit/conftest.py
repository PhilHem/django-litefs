"""Pytest configuration for Django unit tests."""

import os

import pytest

from .fakes import (
    FakeMountValidator,
    FakeNodeIDResolver,
    FakePrimaryDetector,
    FakePrimaryInitializer,
    FakePrimaryMarkerWriter,
)


@pytest.fixture(scope="session", autouse=True)
def _configure_django():
    """Configure Django once per test session."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django.conf.global_settings")

    try:
        import django
        from django.conf import settings

        if not settings.configured:
            settings.configure(
                DEBUG=True,
                DATABASES={
                    "default": {
                        "ENGINE": "django.db.backends.sqlite3",
                        "NAME": ":memory:",
                    }
                },
                INSTALLED_APPS=[],
                USE_TZ=True,
                SECRET_KEY="test-secret-key-for-unit-tests",
            )
            django.setup()

        yield
    except ImportError:
        # Django not available - tests will skip
        yield


def create_litefs_settings_dict(mount_path, db_name="test.db"):
    """Create a settings_dict for LiteFS database backend testing.

    Django 5.x requires additional fields in settings_dict.
    """
    return {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": db_name,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "OPTIONS": {
            "litefs_mount_path": str(mount_path),
        },
    }


@pytest.fixture
def fake_primary_detector():
    """Provide FakePrimaryDetector for unit tests.

    Use instead of mocking PrimaryDetector for cleaner, faster tests.

    Example:
        def test_write_on_replica(fake_primary_detector):
            fake_primary_detector.set_primary(False)
            cursor = LiteFSCursor(conn, fake_primary_detector)
            with pytest.raises(NotPrimaryError):
                cursor.execute("INSERT ...")
    """
    return FakePrimaryDetector()


@pytest.fixture
def django_settings_reset():
    """Reset Django settings to original state after test.

    Saves original settings, allows modification during test, restores on teardown.
    Useful for tests that modify Django settings.

    Example:
        def test_settings_modification(django_settings_reset):
            from django.conf import settings
            settings.SOME_SETTING = "new_value"
            # Test code here
            # Settings will be restored automatically
    """
    from django.test import override_settings

    # Use Django's override_settings context manager for proper isolation
    # This handles unpicklable objects and module references correctly
    with override_settings():
        yield


@pytest.fixture
def mock_installation_checker():
    """Mock InstallationChecker and FilesystemBinaryResolver for command tests.

    This fixture mocks the binary installation check components so that
    tests can run without requiring an actual LiteFS binary to be present.
    By default, returns a successful installation check result.
    """
    from pathlib import Path
    from unittest.mock import Mock, patch

    from litefs.usecases.installation_checker import InstallationCheckResult

    binary_path = Path("/usr/local/bin/litefs")

    with patch(
        "litefs_django.management.commands.litefs_check.FilesystemBinaryResolver"
    ) as mock_resolver:
        with patch(
            "litefs_django.management.commands.litefs_check.InstallationChecker"
        ) as mock_checker:
            mock_resolver.return_value.resolve.return_value = Mock(path=binary_path)
            mock_checker.return_value.return_value = (
                InstallationCheckResult.create_success(binary_path)
            )
            yield {
                "resolver": mock_resolver,
                "checker": mock_checker,
                "binary_path": binary_path,
            }


@pytest.fixture
def fake_mount_validator():
    """Provide FakeMountValidator for unit tests.

    Use instead of mocking MountValidator for cleaner, faster tests.

    Example:
        def test_mount_validation_fails(fake_mount_validator):
            fake_mount_validator.set_error(Exception("Mount not found"))
            # Test code that handles validation failure
    """
    return FakeMountValidator()


@pytest.fixture
def fake_node_id_resolver():
    """Provide FakeNodeIDResolver for unit tests.

    Use instead of mocking NodeIDResolver for cleaner, faster tests.

    Example:
        def test_primary_node_detection(fake_node_id_resolver):
            fake_node_id_resolver.set_node_id("primary-node")
            # Test code that uses node ID
    """
    return FakeNodeIDResolver()


@pytest.fixture
def fake_primary_initializer():
    """Provide FakePrimaryInitializer for unit tests.

    Use instead of mocking PrimaryInitializer for cleaner, faster tests.

    Example:
        def test_static_mode_primary(fake_primary_initializer):
            fake_primary_initializer.set_primary(True)
            # Test code that checks primary status
    """
    return FakePrimaryInitializer()


@pytest.fixture
def fake_primary_marker_writer():
    """Provide FakePrimaryMarkerWriter for unit tests.

    Use instead of mocking PrimaryMarkerWriter for cleaner, faster tests.

    Example:
        def test_marker_writing(fake_primary_marker_writer):
            fake_primary_marker_writer.write_marker("node1")
            assert fake_primary_marker_writer.read_marker() == "node1"
    """
    return FakePrimaryMarkerWriter()
