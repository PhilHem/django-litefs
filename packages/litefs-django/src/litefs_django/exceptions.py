"""Django adapter exceptions."""

from django.db import DatabaseError


class NotPrimaryError(DatabaseError):
    """Raised when a write operation is attempted on a replica node."""

    pass




