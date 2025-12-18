"""Tests for Django LiteFS adapter.

This module sets up Django configuration before any test modules are imported.
"""

import os

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
