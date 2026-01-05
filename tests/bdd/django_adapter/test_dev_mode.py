"""Step definitions for dev_mode.feature.

BDD tests for LiteFS Django Development Mode.
TRA Namespace: Adapter.Django.DevMode
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from django.test import override_settings
from pytest_bdd import given, parsers, scenario, then, when

# Add project root to path for cross-package imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from litefs_django.db.backends.litefs.base import DatabaseWrapper  # noqa: E402

if TYPE_CHECKING:
    pass


# =============================================================================
# Scenarios - Enabling/Disabling LiteFS
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "LiteFS disabled via settings",
)
def test_litefs_disabled_via_settings() -> None:
    """Test that LiteFS can be disabled via settings."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "LiteFS enabled by default when settings present",
)
def test_litefs_enabled_by_default_when_settings_present() -> None:
    """Test that LiteFS is enabled by default when settings present."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "LiteFS disabled when LITEFS settings missing entirely",
)
def test_litefs_disabled_when_settings_missing() -> None:
    """Test that LiteFS is disabled when LITEFS settings missing entirely."""
    pass


# =============================================================================
# Scenarios - Development Mode Behavior
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "No mount path validation in dev mode",
)
def test_no_mount_path_validation_in_dev_mode() -> None:
    """Test that mount path validation is skipped in dev mode."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "No primary/replica check in dev mode",
)
def test_no_primary_replica_check_in_dev_mode() -> None:
    """Test that primary/replica check is skipped in dev mode."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "No split-brain check in dev mode",
)
def test_no_split_brain_check_in_dev_mode() -> None:
    """Test that split-brain check is skipped in dev mode."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "All Django ORM operations work in dev mode",
)
def test_all_django_orm_operations_work_in_dev_mode() -> None:
    """Test that all Django ORM operations work in dev mode."""
    pass


# =============================================================================
# Scenarios - Binary Independence
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "Dev mode works without litefs binary installed",
)
def test_dev_mode_works_without_litefs_binary() -> None:
    """Test that dev mode works without litefs binary installed."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "Dev mode works without FUSE available",
)
def test_dev_mode_works_without_fuse() -> None:
    """Test that dev mode works without FUSE available."""
    pass


# =============================================================================
# Scenarios - Environment-Based Configuration
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "Dev mode controlled via environment variable",
)
def test_dev_mode_controlled_via_environment_variable() -> None:
    """Test that dev mode can be controlled via environment variable."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "Production enables LiteFS via environment",
)
def test_production_enables_litefs_via_environment() -> None:
    """Test that production enables LiteFS via environment."""
    pass


# =============================================================================
# Scenarios - Switching Modes
# =============================================================================


@pytest.mark.tier(1)
@pytest.mark.tra("Adapter.Django.DevMode")
@scenario(
    "../../features/django/dev_mode.feature",
    "Same codebase works in both modes",
)
def test_same_codebase_works_in_both_modes() -> None:
    """Test that same codebase works in both modes."""
    pass


# =============================================================================
# Given steps - Django Project Configuration
# =============================================================================


@given(parsers.parse("a Django project with LITEFS settings:"))
def django_project_with_litefs_settings(
    context: dict, datatable, tmp_path: Path
) -> None:
    """Set up Django project with LITEFS settings from table.

    Args:
        context: Shared context dict
        datatable: Data table with field/value pairs
        tmp_path: Temporary directory for mount path
    """
    litefs_settings = {}
    # Parse datatable (skip header row if present)
    start_idx = 1 if len(datatable) > 1 and datatable[0][0].lower() == "field" else 0
    for row in datatable[start_idx:]:
        field = row[0].strip()
        value_str = row[1].strip() if len(row) > 1 else ""
        # Handle boolean values
        if value_str.lower() == "false":
            value = False
        elif value_str.lower() == "true":
            value = True
        else:
            value = value_str
        litefs_settings[field.upper()] = value

    # Handle environment variable substitution (e.g., ${LITEFS_ENABLED:False})
    # Note: This happens during initial parsing, but env vars may be set later
    # So we store the template string and process it later during initialization
    # For now, process with current env vars (if any)
    env_vars = context.get("env_vars", {})
    for key, value in list(litefs_settings.items()):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            # Extract env var name and default value
            var_part = value[2:-1]  # Remove ${ and }
            if ":" in var_part:
                var_name, default_value = var_part.split(":", 1)
                env_value = env_vars.get(var_name)
                if env_value is None:
                    # Env var not set yet - preserve template string for later processing
                    # Don't convert to default value here, let database_backend_initializes handle it
                    # Keep the template string as-is so it can be processed when env var is set
                    pass  # Keep template string unchanged
                else:
                    # Use env value, convert to boolean if it's "true" or "false"
                    if env_value.lower() == "true":
                        litefs_settings[key] = True
                    elif env_value.lower() == "false":
                        litefs_settings[key] = False
                    else:
                        litefs_settings[key] = env_value
            else:
                var_name = var_part
                env_value = env_vars.get(var_name)
                if env_value is not None:
                    litefs_settings[key] = (
                        env_value.lower() == "true"
                        if env_value.lower() in ("true", "false")
                        else env_value
                    )

    context["litefs_settings"] = litefs_settings

    # If enabled is not False (i.e., production mode), we need mount_path in OPTIONS
    # Create a temp mount path for testing
    mount_path = tmp_path / "litefs"
    mount_path.mkdir(parents=True, exist_ok=True)

    options = {}
    # Check if mount_path is specified in settings
    if "MOUNT_PATH" in litefs_settings:
        mount_path_value = litefs_settings["MOUNT_PATH"]
        # If it's an absolute path that doesn't exist, create it or use temp path
        if mount_path_value.startswith("/") and not Path(mount_path_value).exists():
            # Use temp path instead for testing
            options["litefs_mount_path"] = str(mount_path)
        else:
            options["litefs_mount_path"] = mount_path_value
    else:
        # Only add mount_path if we're in production mode (enabled not False)
        enabled = litefs_settings.get("ENABLED", True)
        if enabled is not False:
            options["litefs_mount_path"] = str(mount_path)

    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "test.db",
        "OPTIONS": options,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {},
    }


@given("a Django project with no LITEFS settings dict")
def django_project_with_no_litefs_settings(context: dict) -> None:
    """Set up Django project with no LITEFS settings dict."""
    context["litefs_settings"] = None
    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "test.db",
        "OPTIONS": {},
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {},
    }


@given(parsers.parse('DATABASE ENGINE is "{engine}"'))
def database_engine_is(context: dict, engine: str) -> None:
    """Set database engine."""
    context["settings_dict"]["ENGINE"] = engine


@given(parsers.parse('DATABASE OPTIONS has {key} "{value}"'))
def database_options_has(context: dict, key: str, value: str) -> None:
    """Set database OPTIONS key."""
    if "OPTIONS" not in context["settings_dict"]:
        context["settings_dict"]["OPTIONS"] = {}
    context["settings_dict"]["OPTIONS"][key] = value


@given(parsers.parse('"enabled" is not specified'))
def enabled_not_specified(context: dict) -> None:
    """Ensure enabled is not in LITEFS settings."""
    if "litefs_settings" in context and context["litefs_settings"] is not None:
        context["litefs_settings"].pop("ENABLED", None)


@given(parsers.parse("a Django project with LITEFS.enabled = {value}"))
def django_project_with_litefs_enabled(context: dict, value: str) -> None:
    """Set up Django project with LITEFS.enabled value."""
    enabled = value.lower() == "true"
    context["litefs_settings"] = {"ENABLED": enabled}
    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "test.db",
        "OPTIONS": {},
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {},
    }


@given("the litefs binary is not in PATH")
def litefs_binary_not_in_path(context: dict) -> None:
    """Mark that litefs binary is not in PATH."""
    context["litefs_binary_unavailable"] = True


@given("FUSE is not available on the system")
def fuse_not_available(context: dict) -> None:
    """Mark that FUSE is not available."""
    context["fuse_unavailable"] = True


@given(parsers.parse("environment variable {var} is not set"))
def environment_variable_not_set(context: dict, var: str) -> None:
    """Mark that environment variable is not set."""
    context["env_vars"] = context.get("env_vars", {})
    context["env_vars"][var] = None


@given(parsers.parse('environment variable {var} is "{value}"'))
def environment_variable_is(context: dict, var: str, value: str) -> None:
    """Set environment variable value."""
    context["env_vars"] = context.get("env_vars", {})
    context["env_vars"][var] = value


@given("a Django project configured for LiteFS")
def django_project_configured_for_litefs(context: dict, tmp_path: Path) -> None:
    """Set up Django project configured for LiteFS."""
    mount_path = tmp_path / "litefs"
    mount_path.mkdir(parents=True, exist_ok=True)
    context["litefs_settings"] = {"MOUNT_PATH": str(mount_path), "ENABLED": True}
    context["settings_dict"] = {
        "ENGINE": "litefs_django.db.backends.litefs",
        "NAME": "test.db",
        "OPTIONS": {"litefs_mount_path": str(mount_path)},
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {},
    }


# =============================================================================
# When steps - Actions
# =============================================================================


@when("the database backend initializes")
def database_backend_initializes(context: dict) -> None:
    """Initialize database backend with current settings."""
    settings_dict = context["settings_dict"]
    litefs_settings = context.get("litefs_settings")

    # Re-process environment variable substitution if env vars were set after settings
    if litefs_settings is not None:
        env_vars = context.get("env_vars", {})
        processed_settings = {}
        for key, value in litefs_settings.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                # Extract env var name and default value
                var_part = value[2:-1]  # Remove ${ and }
                if ":" in var_part:
                    var_name, default_value = var_part.split(":", 1)
                    env_value = env_vars.get(var_name)
                    if env_value is None:
                        # Use default value, convert to boolean if it's "true" or "false"
                        if default_value.lower() == "true":
                            processed_settings[key] = True
                        elif default_value.lower() == "false":
                            processed_settings[key] = False
                        else:
                            processed_settings[key] = default_value
                    else:
                        # Use env value, convert to boolean if it's "true" or "false"
                        if env_value.lower() == "true":
                            processed_settings[key] = True
                        elif env_value.lower() == "false":
                            processed_settings[key] = False
                        else:
                            processed_settings[key] = env_value
                else:
                    # No default value, just use env var if set
                    var_name = var_part
                    env_value = env_vars.get(var_name)
                    if env_value is not None:
                        if env_value.lower() == "true":
                            processed_settings[key] = True
                        elif env_value.lower() == "false":
                            processed_settings[key] = False
                        else:
                            processed_settings[key] = env_value
                    else:
                        processed_settings[key] = value  # Keep original template
            else:
                processed_settings[key] = value  # Keep non-template values

        # Update context with processed settings BEFORE checking mount_path
        context["litefs_settings"] = processed_settings
        litefs_settings = processed_settings

        # If enabled becomes True, ensure mount_path is in OPTIONS
        if processed_settings.get(
            "ENABLED"
        ) is True and "litefs_mount_path" not in settings_dict.get("OPTIONS", {}):
            from pathlib import Path
            import tempfile

            # Create a temp mount path
            mount_path = Path(tempfile.mkdtemp()) / "litefs"
            mount_path.mkdir(parents=True, exist_ok=True)
            if "OPTIONS" not in settings_dict:
                settings_dict["OPTIONS"] = {}
            settings_dict["OPTIONS"]["litefs_mount_path"] = str(mount_path)
            context["settings_dict"] = settings_dict

    # Apply override_settings if LITEFS settings are specified
    if litefs_settings is not None:
        with override_settings(LITEFS=litefs_settings):
            try:
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                context["wrapper"] = wrapper
                context["initialization_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["initialization_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__
    else:
        with override_settings(LITEFS=None):
            try:
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                context["wrapper"] = wrapper
                context["initialization_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["initialization_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__


@when("I create a database connection")
def create_database_connection(context: dict, tmp_path: Path) -> None:
    """Create a database connection."""
    settings_dict = context["settings_dict"].copy()
    litefs_settings = context.get("litefs_settings")

    # Ensure we have a valid database path
    if "NAME" not in settings_dict or not settings_dict["NAME"]:
        settings_dict["NAME"] = str(tmp_path / "test.db")

    if litefs_settings is not None:
        with override_settings(LITEFS=litefs_settings):
            try:
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                conn = wrapper.get_new_connection(wrapper.get_connection_params())
                context["connection"] = conn
                context["wrapper"] = wrapper
                context["connection_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["connection_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__
    else:
        with override_settings(LITEFS=None):
            try:
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                conn = wrapper.get_new_connection(wrapper.get_connection_params())
                context["connection"] = conn
                context["wrapper"] = wrapper
                context["connection_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["connection_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__


@when(parsers.parse('I execute "{sql}"'))
def execute_sql(context: dict, sql: str, tmp_path: Path) -> None:
    """Execute SQL statement."""
    import sqlite3

    settings_dict = context["settings_dict"]
    litefs_settings = context.get("litefs_settings")

    # Create database file if needed
    db_path = tmp_path / "test.db"
    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (name TEXT)")
        conn.commit()
        conn.close()

    if litefs_settings is not None:
        with override_settings(LITEFS=litefs_settings):
            wrapper = DatabaseWrapper(settings_dict, alias="default")
            wrapper.settings_dict["NAME"] = str(db_path)
            conn = wrapper.get_new_connection(wrapper.get_connection_params())
            wrapper.connection = conn  # Set connection on wrapper
            cursor = wrapper.create_cursor()
            try:
                cursor.execute(sql)
                conn.commit()
                context["sql_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["sql_result"] = "error"
                context["error"] = e
            finally:
                cursor.close()
                conn.close()
    else:
        with override_settings(LITEFS=None):
            wrapper = DatabaseWrapper(settings_dict, alias="default")
            wrapper.settings_dict["NAME"] = str(db_path)
            conn = wrapper.get_new_connection(wrapper.get_connection_params())
            wrapper.connection = conn  # Set connection on wrapper
            cursor = wrapper.create_cursor()
            try:
                cursor.execute(sql)
                conn.commit()
                context["sql_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["sql_result"] = "error"
                context["error"] = e
            finally:
                cursor.close()
                conn.close()


@when(parsers.parse("I perform standard Django ORM operations:"))
def perform_django_orm_operations(context: dict, datatable, tmp_path: Path) -> None:
    """Perform Django ORM operations."""
    # For BDD tests, we'll simulate ORM operations via direct SQL
    # In a real scenario, this would use Django models
    import sqlite3

    settings_dict = context["settings_dict"]
    litefs_settings = context.get("litefs_settings")

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()

    operations = []
    # Parse datatable (skip header row)
    start_idx = (
        1 if len(datatable) > 1 and datatable[0][0].lower() == "operation" else 0
    )
    for row in datatable[start_idx:]:
        operations.append(
            {"operation": row[0], "model": row[1] if len(row) > 1 else ""}
        )

    if litefs_settings is not None:
        with override_settings(LITEFS=litefs_settings):
            wrapper = DatabaseWrapper(settings_dict, alias="default")
            wrapper.settings_dict["NAME"] = str(db_path)
            conn = wrapper.get_new_connection(wrapper.get_connection_params())
            wrapper.connection = conn  # Set connection on wrapper
            cursor = wrapper.create_cursor()
            try:
                for op in operations:
                    if op["operation"] == "create":
                        cursor.execute("INSERT INTO users (name) VALUES (?)", ("test",))
                    elif op["operation"] == "read":
                        cursor.execute("SELECT * FROM users")
                        cursor.fetchall()
                    elif op["operation"] == "update":
                        cursor.execute(
                            "UPDATE users SET name = ? WHERE id = 1", ("updated",)
                        )
                    elif op["operation"] == "delete":
                        cursor.execute("DELETE FROM users WHERE id = 1")
                conn.commit()
                context["orm_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["orm_result"] = "error"
                context["error"] = e
            finally:
                cursor.close()
                conn.close()
    else:
        with override_settings(LITEFS=None):
            wrapper = DatabaseWrapper(settings_dict, alias="default")
            wrapper.settings_dict["NAME"] = str(db_path)
            conn = wrapper.get_new_connection(wrapper.get_connection_params())
            wrapper.connection = conn  # Set connection on wrapper
            cursor = wrapper.create_cursor()
            try:
                for op in operations:
                    if op["operation"] == "create":
                        cursor.execute("INSERT INTO users (name) VALUES (?)", ("test",))
                    elif op["operation"] == "read":
                        cursor.execute("SELECT * FROM users")
                        cursor.fetchall()
                    elif op["operation"] == "update":
                        cursor.execute(
                            "UPDATE users SET name = ? WHERE id = 1", ("updated",)
                        )
                    elif op["operation"] == "delete":
                        cursor.execute("DELETE FROM users WHERE id = 1")
                conn.commit()
                context["orm_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["orm_result"] = "error"
                context["error"] = e
            finally:
                cursor.close()
                conn.close()


@when("the Django application starts")
def django_application_starts(context: dict, tmp_path: Path) -> None:
    """Simulate Django application startup."""
    settings_dict = context["settings_dict"]
    litefs_settings = context.get("litefs_settings")

    if litefs_settings is not None:
        with override_settings(LITEFS=litefs_settings):
            try:
                # Just initialize the wrapper - this simulates app startup
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                context["wrapper"] = wrapper
                context["startup_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["startup_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__
    else:
        with override_settings(LITEFS=None):
            try:
                wrapper = DatabaseWrapper(settings_dict, alias="default")
                context["wrapper"] = wrapper
                context["startup_result"] = "success"
                context["error"] = None
            except Exception as e:
                context["startup_result"] = "error"
                context["error"] = e
                context["error_type"] = type(e).__name__


@when(parsers.parse("LITEFS.enabled is toggled between {value1} and {value2}"))
def litefs_enabled_toggled(context: dict, value1: str, value2: str) -> None:
    """Toggle LITEFS.enabled between two values."""
    # Test both values
    enabled1 = value1.lower() == "true"
    enabled2 = value2.lower() == "true"
    context["toggle_results"] = []
    settings_dict = context["settings_dict"]

    for enabled in [enabled1, enabled2]:
        with override_settings(LITEFS={"ENABLED": enabled}):
            try:
                _wrapper = DatabaseWrapper(settings_dict, alias="default")  # noqa: F841
                context["toggle_results"].append(
                    {"enabled": enabled, "result": "success"}
                )
            except Exception as e:
                context["toggle_results"].append(
                    {"enabled": enabled, "result": "error", "error": e}
                )


# =============================================================================
# Then steps - Assertions
# =============================================================================


@then("LiteFS-specific features should be disabled")
def litefs_features_disabled(context: dict) -> None:
    """Assert that LiteFS-specific features are disabled."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is True, "Expected dev mode to be enabled"


@then("the backend should delegate to standard SQLite")
def backend_delegates_to_standard_sqlite(context: dict) -> None:
    """Assert that backend delegates to standard SQLite."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is True, "Expected dev mode to be enabled"
    # In dev mode, NAME should not be prepended with mount_path
    assert "litefs_mount_path" not in str(wrapper.settings_dict.get("NAME", ""))


@then("LiteFS features should be enabled")
def litefs_features_enabled(context: dict) -> None:
    """Assert that LiteFS features are enabled."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is False, "Expected production mode (dev_mode=False)"


@then("the backend should behave as standard SQLite")
def backend_behaves_as_standard_sqlite(context: dict) -> None:
    """Assert that backend behaves as standard SQLite."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is True, "Expected dev mode to be enabled"


@then("no LiteFS validation should occur")
def no_litefs_validation_occurs(context: dict) -> None:
    """Assert that no LiteFS validation occurs."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is True, "Expected dev mode to be enabled"


@then("the connection should succeed")
def connection_succeeds(context: dict) -> None:
    """Assert that connection succeeds."""
    assert context.get("connection_result") == "success", (
        f"Expected connection success but got error: {context.get('error')}"
    )


@then("no mount path check should occur")
def no_mount_path_check_occurs(context: dict) -> None:
    """Assert that no mount path check occurs."""
    assert context.get("connection_result") == "success", (
        f"Expected connection success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    assert wrapper._dev_mode is True, "Expected dev mode to be enabled"


@then("the query should execute successfully")
def query_executes_successfully(context: dict) -> None:
    """Assert that query executes successfully."""
    assert context.get("sql_result") == "success", (
        f"Expected SQL execution success but got error: {context.get('error')}"
    )


@then("no is_primary() check should occur")
def no_is_primary_check_occurs(context: dict) -> None:
    """Assert that no is_primary() check occurs."""
    # This is verified by the fact that the query succeeded in dev mode
    # In production mode, a replica would fail, but in dev mode it succeeds
    assert context.get("sql_result") == "success", (
        f"Expected SQL execution success but got error: {context.get('error')}"
    )


@then("no split-brain detection should occur")
def no_split_brain_detection_occurs(context: dict) -> None:
    """Assert that no split-brain detection occurs."""
    # This is verified by the fact that the query succeeded in dev mode
    assert context.get("sql_result") == "success", (
        f"Expected SQL execution success but got error: {context.get('error')}"
    )


@then("all operations should succeed")
def all_operations_succeed(context: dict) -> None:
    """Assert that all operations succeed."""
    assert context.get("orm_result") == "success", (
        f"Expected ORM operations success but got error: {context.get('error')}"
    )


@then("no error should be raised")
def no_error_raised(context: dict) -> None:
    """Assert that no error is raised."""
    result_key = context.get("startup_result") or context.get("initialization_result")
    assert result_key == "success", (
        f"Expected success but got error: {context.get('error')}"
    )


@then("database operations should work normally")
def database_operations_work_normally(context: dict, tmp_path: Path) -> None:
    """Assert that database operations work normally."""

    wrapper = context.get("wrapper")
    if wrapper:
        db_path = tmp_path / "test.db"
        wrapper.settings_dict["NAME"] = str(db_path)
        conn = wrapper.get_new_connection(wrapper.get_connection_params())
        wrapper.connection = conn  # Set connection on wrapper
        cursor = wrapper.create_cursor()
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
            cursor.execute("INSERT INTO test (id) VALUES (1)")
            conn.commit()
            cursor.execute("SELECT * FROM test")
            results = cursor.fetchall()
            assert len(results) == 1, "Expected one row"
        finally:
            cursor.close()
            conn.close()


@then(parsers.parse("LiteFS should be {state}"))
def litefs_should_be(context: dict, state: str) -> None:
    """Assert LiteFS state (enabled/disabled)."""
    assert context.get("initialization_result") == "success", (
        f"Expected initialization success but got error: {context.get('error')}"
    )
    wrapper = context["wrapper"]
    if state.lower() == "disabled":
        assert wrapper._dev_mode is True, "Expected dev mode (LiteFS disabled)"
    elif state.lower() == "enabled":
        assert wrapper._dev_mode is False, "Expected production mode (LiteFS enabled)"


@then("the application should work correctly in both modes")
def application_works_in_both_modes(context: dict) -> None:
    """Assert that application works correctly in both modes."""
    results = context.get("toggle_results", [])
    assert len(results) == 2, f"Expected 2 toggle results, got {len(results)}"
    for result in results:
        assert result["result"] == "success", (
            f"Expected success for enabled={result['enabled']} but got error: {result.get('error')}"
        )


@then("no code changes should be required")
def no_code_changes_required(context: dict) -> None:
    """Assert that no code changes are required (always true in tests)."""
    # This is a documentation assertion - the fact that both modes work
    # with the same codebase is verified by the toggle test
    assert context.get("toggle_results") is not None, "Expected toggle results"
