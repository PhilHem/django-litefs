"""AppConfig for example app."""

from django.apps import AppConfig


class MyAppConfig(AppConfig):
    """Configuration for myapp."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"
