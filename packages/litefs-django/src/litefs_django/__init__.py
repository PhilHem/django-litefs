"""Django adapter for LiteFS SQLite replication."""

from litefs_django.apps import LiteFSDjangoConfig
from litefs_django.exceptions import NotPrimaryError, SplitBrainError
from litefs_django.settings import get_litefs_settings
from litefs_django.signals import split_brain_detected

__version__ = "0.1.0"

__all__ = [
    "LiteFSDjangoConfig",
    "NotPrimaryError",
    "SplitBrainError",
    "get_litefs_settings",
    "split_brain_detected",
]
