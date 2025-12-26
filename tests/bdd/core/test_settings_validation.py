"""Step definitions for settings domain validation feature."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from litefs.domain.settings import LiteFSSettings
from litefs.domain.exceptions import LiteFSConfigError


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Paths must be absolute",
)
def test_paths_must_be_absolute():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Path traversal attacks are rejected in mount_path",
)
def test_path_traversal_mount_path():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Path traversal attacks are rejected in data_path",
)
def test_path_traversal_data_path():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Database name cannot be empty",
)
def test_database_name_empty():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Database name cannot be whitespace only",
)
def test_database_name_whitespace():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Leader election must be 'static' or 'raft'",
)
def test_leader_election_invalid():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Static leader election is valid",
)
def test_static_election_valid():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Raft leader election is valid with proper config",
)
def test_raft_election_valid():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Raft mode requires raft_self_addr",
)
def test_raft_requires_self_addr():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Raft mode requires non-empty raft_self_addr",
)
def test_raft_requires_nonempty_self_addr():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Raft mode requires raft_peers",
)
def test_raft_requires_peers():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Raft mode rejects empty peers list",
)
def test_raft_rejects_empty_peers():
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant")
@scenario(
    "../../features/core/settings_validation.feature",
    "Static mode ignores raft fields even if invalid",
)
def test_static_ignores_raft_fields():
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {
        "kwargs": {},
        "result": None,
        "error": None,
    }


def _base_valid_kwargs() -> dict:
    """Return base valid kwargs for LiteFSSettings."""
    return {
        "mount_path": "/litefs",
        "data_path": "/var/lib/litefs",
        "database_name": "db.sqlite3",
        "leader_election": "static",
        "proxy_addr": ":8080",
        "enabled": True,
        "retention": "1h",
    }


def _try_create_settings(context: dict) -> None:
    """Attempt to create LiteFSSettings and capture result or error."""
    try:
        context["result"] = LiteFSSettings(**context["kwargs"])
        context["error"] = None
    except LiteFSConfigError as e:
        context["result"] = None
        context["error"] = e


# ---------------------------------------------------------------------------
# Given Steps - Settings with Specific Field Values
# ---------------------------------------------------------------------------

@given(parsers.parse('LiteFS settings with mount_path "{value}"'))
def settings_with_mount_path(context: dict, value: str):
    """Create settings kwargs with custom mount_path."""
    context["kwargs"] = _base_valid_kwargs()
    context["kwargs"]["mount_path"] = value
    _try_create_settings(context)


@given(parsers.parse('LiteFS settings with data_path "{value}"'))
def settings_with_data_path(context: dict, value: str):
    """Create settings kwargs with custom data_path."""
    context["kwargs"] = _base_valid_kwargs()
    context["kwargs"]["data_path"] = value
    _try_create_settings(context)


@given(parsers.parse('LiteFS settings with database_name "{value}"'))
def settings_with_database_name(context: dict, value: str):
    """Create settings kwargs with custom database_name."""
    context["kwargs"] = _base_valid_kwargs()
    context["kwargs"]["database_name"] = value
    _try_create_settings(context)


@given("LiteFS settings with empty database_name")
def settings_with_empty_database_name(context: dict):
    """Create settings kwargs with empty database_name."""
    context["kwargs"] = _base_valid_kwargs()
    context["kwargs"]["database_name"] = ""
    _try_create_settings(context)


@given(parsers.parse('LiteFS settings with leader_election "{value}"'))
def settings_with_leader_election(context: dict, value: str):
    """Create settings kwargs with custom leader_election (deferred creation)."""
    context["kwargs"] = _base_valid_kwargs()
    context["kwargs"]["leader_election"] = value
    # Don't create yet - more given steps may follow


# ---------------------------------------------------------------------------
# Given Steps - Raft Configuration
# ---------------------------------------------------------------------------

@given(parsers.parse('raft_self_addr "{value}"'))
def set_raft_self_addr(context: dict, value: str):
    """Set raft_self_addr in kwargs."""
    context["kwargs"]["raft_self_addr"] = value


@given("raft_self_addr is empty")
def set_raft_self_addr_empty(context: dict):
    """Set raft_self_addr to empty string."""
    context["kwargs"]["raft_self_addr"] = ""


@given("raft_self_addr is not set")
def raft_self_addr_not_set(context: dict):
    """Ensure raft_self_addr is None."""
    context["kwargs"]["raft_self_addr"] = None


@given(parsers.parse('raft_peers "{value}"'))
def set_raft_peers(context: dict, value: str):
    """Set raft_peers from comma-separated string."""
    context["kwargs"]["raft_peers"] = value.split(",")


@given("raft_peers is not set")
def raft_peers_not_set(context: dict):
    """Ensure raft_peers is None."""
    context["kwargs"]["raft_peers"] = None


@given("raft_peers is empty list")
def raft_peers_empty(context: dict):
    """Set raft_peers to empty list."""
    context["kwargs"]["raft_peers"] = []


# ---------------------------------------------------------------------------
# Then Steps - Deferred Creation and Assertions
# ---------------------------------------------------------------------------

@then("a LiteFSConfigError should be raised")
def error_raised(context: dict):
    """Assert that a LiteFSConfigError was raised."""
    # Try to create if not already attempted
    if context["result"] is None and context["error"] is None:
        _try_create_settings(context)

    assert context["error"] is not None, "Expected LiteFSConfigError but none was raised"
    assert isinstance(context["error"], LiteFSConfigError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None, "No error was raised"
    assert text in str(context["error"]), f"Expected '{text}' in '{context['error']}'"


@then("the settings should be valid")
def settings_valid(context: dict):
    """Assert that settings were created successfully."""
    # Try to create if not already attempted
    if context["result"] is None and context["error"] is None:
        _try_create_settings(context)

    assert context["error"] is None, f"Unexpected error: {context['error']}"
    assert context["result"] is not None
