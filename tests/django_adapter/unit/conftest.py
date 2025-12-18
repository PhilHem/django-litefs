"""Pytest configuration for Django unit tests."""

import os

import pytest

# Set Django settings module before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django.conf.global_settings")

try:
    import django
    from django.conf import settings

    # Configure Django settings if not already configured
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
except ImportError:
    # Django not available - tests will skip
    pass


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
