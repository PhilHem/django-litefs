"""Django app configuration for LiteFS."""

import logging
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings as django_settings

from litefs_django.settings import get_litefs_settings
from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError

logger = logging.getLogger(__name__)


class LiteFSDjangoConfig(AppConfig):
    """Django app configuration for LiteFS adapter."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "litefs_django"
    verbose_name = "LiteFS Django Adapter"

    def ready(self):
        """Validate LiteFS settings and check availability on startup."""
        # Only validate if LiteFS is enabled
        litefs_config = getattr(django_settings, "LITEFS", None)
        if not litefs_config:
            logger.warning(
                "LITEFS settings not found. LiteFS adapter may not work correctly."
            )
            return

        # Check if LiteFS is enabled
        if not litefs_config.get("ENABLED", True):
            logger.info("LiteFS is disabled in settings.")
            return

        try:
            # Convert Django settings to domain object (validates settings)
            litefs_settings = get_litefs_settings(litefs_config)

            # Check if LiteFS mount path exists
            mount_path = Path(litefs_settings.mount_path)
            if not mount_path.exists():
                logger.warning(
                    f"LiteFS mount path does not exist: {mount_path}. "
                    "LiteFS may not be running or mounted."
                )
                return

            # Check if this node is primary (optional, for logging)
            try:
                detector = PrimaryDetector(litefs_settings.mount_path)
                is_primary = detector.is_primary()
                logger.info(
                    f"LiteFS initialized. Node is {'primary' if is_primary else 'replica'}."
                )
            except LiteFSNotRunningError:
                logger.warning("LiteFS is not running or mount path is invalid.")

        except Exception as e:
            logger.error(f"Failed to validate LiteFS settings: {e}")
            # Don't raise - allow Django to start even if LiteFS config is invalid
            # Application will fail when trying to use database backend

