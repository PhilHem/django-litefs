"""Django adapter for LiteFS SQLite replication."""

from litefs_django.signals import split_brain_detected

__version__ = "0.1.0"

__all__ = [
    "split_brain_detected",
]




