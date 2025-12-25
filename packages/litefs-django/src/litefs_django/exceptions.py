"""Django adapter exceptions.

Exception hierarchy:
- NotPrimaryError: Django-specific exception for write operations on replicas.
  Inherits from Django's DatabaseError to integrate with Django's error handling.
  The underlying domain logic uses LiteFSNotRunningError (from domain) for
  configuration issues, but this adapter exception is raised for runtime
  write operation violations.

Relationship to domain exceptions:
- Domain exceptions (LiteFSConfigError, LiteFSNotRunningError) are raised
  by use cases and represent configuration/state errors.
- Adapter exceptions (NotPrimaryError) are raised by framework adapters
  and represent framework-specific error conditions.
"""

from django.db import DatabaseError


class NotPrimaryError(DatabaseError):
    """Raised when a write operation is attempted on a replica node.

    This is a Django adapter-specific exception that inherits from
    Django's DatabaseError for integration with Django's error handling.

    Domain exceptions (like LiteFSNotRunningError) are raised by use cases
    for configuration/state issues. This adapter exception is raised by the
    Django backend when write operations are attempted on non-primary nodes.
    """

    pass





