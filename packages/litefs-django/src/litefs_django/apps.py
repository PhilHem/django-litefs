"""Django app configuration for LiteFS."""

import logging
from pathlib import Path
from typing import Callable, Any

from django.apps import AppConfig
from django.conf import settings as django_settings

from litefs_django.settings import get_litefs_settings
from litefs.usecases.mount_validator import MountValidator
from litefs.usecases.primary_detector import PrimaryDetector, LiteFSNotRunningError
from litefs.usecases.primary_initializer import PrimaryInitializer
from litefs.adapters.ports import EnvironmentNodeIDResolver, NodeIDResolverPort

logger = logging.getLogger(__name__)


def _default_mount_validator_factory() -> MountValidator:
    """Default factory for creating MountValidator instances."""
    return MountValidator()


def _default_node_id_resolver_factory() -> NodeIDResolverPort:
    """Default factory for creating NodeIDResolver instances."""
    return EnvironmentNodeIDResolver()


def _default_primary_initializer_factory(
    static_leader_config: Any,
) -> PrimaryInitializer:
    """Default factory for creating PrimaryInitializer instances."""
    return PrimaryInitializer(static_leader_config)


def _default_primary_detector_factory(mount_path: str) -> PrimaryDetector:
    """Default factory for creating PrimaryDetector instances."""
    return PrimaryDetector(mount_path)


class LiteFSDjangoConfig(AppConfig):
    """Django app configuration for LiteFS adapter."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "litefs_django"
    verbose_name = "LiteFS Django Adapter"

    # Dependency injection factories (can be overridden for testing)
    mount_validator_factory: Callable[[], MountValidator] = _default_mount_validator_factory
    node_id_resolver_factory: Callable[[], NodeIDResolverPort] = (
        _default_node_id_resolver_factory
    )
    primary_initializer_factory: Callable[
        [Any], PrimaryInitializer
    ] = _default_primary_initializer_factory
    primary_detector_factory: Callable[
        [str], PrimaryDetector
    ] = _default_primary_detector_factory

    def ready(self) -> None:
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

            # Check if LiteFS mount path exists using MountValidator
            mount_path = Path(litefs_settings.mount_path)
            validator = self.mount_validator_factory()
            try:
                validator.validate(mount_path)
            except Exception as e:
                logger.warning(
                    f"LiteFS mount path validation failed: {e}. "
                    "LiteFS may not be running or mounted."
                )
                return

            # Check if this node is primary (optional, for logging)
            # Use different detection method based on leader_election mode
            try:
                if litefs_settings.leader_election == "static":
                    # Static mode: use PrimaryInitializer with static config
                    if litefs_settings.static_leader_config is None:
                        logger.warning(
                            "Static leader election configured but no static_leader_config found."
                        )
                        return

                    try:
                        # Resolve current node's ID
                        resolver = self.node_id_resolver_factory()
                        current_node_id = resolver.resolve_node_id()

                        # Determine if this node is primary
                        initializer = self.primary_initializer_factory(
                            litefs_settings.static_leader_config
                        )
                        is_primary = initializer.is_primary(current_node_id)

                        logger.info(
                            f"LiteFS initialized (static mode). Node is "
                            f"{'primary' if is_primary else 'replica'}."
                        )
                    except (KeyError, ValueError) as e:
                        logger.warning(
                            f"Failed to resolve node ID for static primary detection: {e}. "
                            "LITEFS_NODE_ID environment variable may not be set or is invalid."
                        )
                else:
                    # Raft mode: use PrimaryDetector for runtime detection
                    detector = self.primary_detector_factory(litefs_settings.mount_path)
                    is_primary = detector.is_primary()
                    logger.info(
                        f"LiteFS initialized (raft mode). Node is "
                        f"{'primary' if is_primary else 'replica'}."
                    )
            except LiteFSNotRunningError:
                logger.warning("LiteFS is not running or mount path is invalid.")

        except Exception as e:
            logger.error(f"Failed to validate LiteFS settings: {e}")
            # Don't raise - allow Django to start even if LiteFS config is invalid
            # Application will fail when trying to use database backend





