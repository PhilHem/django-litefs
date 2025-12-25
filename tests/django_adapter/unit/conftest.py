"""Pytest configuration for Django unit tests."""

import os

import pytest

from .fakes import FakePrimaryDetector


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
