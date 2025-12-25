"""Domain exceptions.

Exception hierarchy:
- LiteFSConfigError: Base domain exception for configuration errors.
  All domain-level validation errors inherit from this.
  Used by use cases and domain entities to signal invalid configuration.
"""


class LiteFSConfigError(Exception):
    """Raised when LiteFS configuration is invalid.

    This is the base exception for all domain-level configuration errors.
    It is raised by domain entities (e.g., LiteFSSettings) and use cases
    (e.g., ConfigParser, MountValidator) when configuration validation fails.

    Framework adapters (Django, FastAPI) may catch this and re-raise as
    framework-specific exceptions, but the domain layer always uses this.
    """

    pass
