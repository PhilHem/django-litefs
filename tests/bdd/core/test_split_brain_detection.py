"""Step definitions for split-brain detection feature."""

import pytest
from dataclasses import FrozenInstanceError
from pytest_bdd import scenario, given, when, then, parsers
from unittest.mock import Mock

from litefs.domain.split_brain import RaftNodeState, RaftClusterState
from litefs.domain.exceptions import LiteFSConfigError
from litefs.usecases.split_brain_detector import SplitBrainDetector, SplitBrainStatus
from litefs.adapters.ports import SplitBrainDetectorPort


# ---------------------------------------------------------------------------
# Scenarios - RaftNodeState Validation
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftNodeState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "RaftNodeState requires non-empty node_id",
)
def test_node_state_empty_node_id():
    """Test that RaftNodeState rejects empty node_id."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftNodeState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "RaftNodeState rejects whitespace-only node_id",
)
def test_node_state_whitespace_node_id():
    """Test that RaftNodeState rejects whitespace-only node_id."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftNodeState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "RaftNodeState accepts valid node_id",
)
def test_node_state_valid():
    """Test that RaftNodeState accepts valid node_id."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - RaftClusterState Validation
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftClusterState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "RaftClusterState requires non-empty nodes list",
)
def test_cluster_state_empty_nodes():
    """Test that RaftClusterState rejects empty nodes list."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftClusterState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "RaftClusterState accepts valid nodes list",
)
def test_cluster_state_valid():
    """Test that RaftClusterState accepts valid nodes list."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - RaftClusterState Leader Counting
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftClusterState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "Cluster with single leader reports one leader",
)
def test_cluster_single_leader():
    """Test cluster with single leader."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftClusterState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "Cluster with no leaders reports zero leaders",
)
def test_cluster_no_leaders():
    """Test cluster with no leaders."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.RaftClusterState")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "Cluster with multiple leaders reports all leaders",
)
def test_cluster_multiple_leaders():
    """Test cluster with multiple leaders."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - SplitBrainDetector Use Case
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.SplitBrainDetector")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "No split-brain when exactly one leader exists",
)
def test_no_split_brain_single_leader():
    """Test no split-brain with single leader."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.SplitBrainDetector")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "No split-brain when zero leaders exist",
)
def test_no_split_brain_zero_leaders():
    """Test no split-brain with zero leaders."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.SplitBrainDetector")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "Split-brain detected when two nodes claim leadership",
)
def test_split_brain_two_leaders():
    """Test split-brain detected with two leaders."""
    pass


@pytest.mark.tier(1)
@pytest.mark.tra("UseCase.SplitBrainDetector")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "Split-brain detected when all nodes claim leadership",
)
def test_split_brain_all_leaders():
    """Test split-brain detected when all nodes claim leadership."""
    pass


# ---------------------------------------------------------------------------
# Scenarios - SplitBrainStatus Immutability
# ---------------------------------------------------------------------------


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.SplitBrainStatus")
@scenario(
    "../../features/core/split_brain_detection.feature",
    "SplitBrainStatus is immutable",
)
def test_split_brain_status_immutable():
    """Test that SplitBrainStatus is immutable."""
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    """Shared context for passing state between steps."""
    return {}


class FakeSplitBrainDetectorPort:
    """Fake port for testing SplitBrainDetector."""

    def __init__(self, cluster_state: RaftClusterState):
        self._cluster_state = cluster_state

    def get_cluster_state(self) -> RaftClusterState:
        return self._cluster_state


# ---------------------------------------------------------------------------
# Given steps - RaftNodeState
# ---------------------------------------------------------------------------


# (No given steps needed for node state creation scenarios)


# ---------------------------------------------------------------------------
# Given steps - RaftClusterState
# ---------------------------------------------------------------------------


@given("a cluster with nodes:")
def cluster_with_nodes(context: dict, datatable):
    """Create a cluster from the datatable.

    Note: datatable is a list of lists where first row is headers.
    """
    nodes = []
    # Skip header row (index 0), process data rows
    for row in datatable[1:]:
        node_id = row[0]  # First column: node_id
        is_leader = row[1].lower() == "true"  # Second column: is_leader
        nodes.append(RaftNodeState(node_id=node_id, is_leader=is_leader))
    context["cluster_state"] = RaftClusterState(nodes=nodes)


# ---------------------------------------------------------------------------
# Given steps - SplitBrainDetector
# ---------------------------------------------------------------------------


@given(parsers.parse('a cluster with single leader "{leader_id}"'))
def cluster_single_leader(context: dict, leader_id: str):
    """Create a cluster with a single leader."""
    nodes = [
        RaftNodeState(node_id=leader_id, is_leader=True),
        RaftNodeState(node_id="node2", is_leader=False),
        RaftNodeState(node_id="node3", is_leader=False),
    ]
    context["cluster_state"] = RaftClusterState(nodes=nodes)


@given("a cluster with no leaders")
def cluster_no_leaders(context: dict):
    """Create a cluster with no leaders."""
    nodes = [
        RaftNodeState(node_id="node1", is_leader=False),
        RaftNodeState(node_id="node2", is_leader=False),
        RaftNodeState(node_id="node3", is_leader=False),
    ]
    context["cluster_state"] = RaftClusterState(nodes=nodes)


@given(parsers.parse('a cluster where "{node1}" and "{node2}" both claim leadership'))
def cluster_two_leaders(context: dict, node1: str, node2: str):
    """Create a cluster with two leaders (split-brain)."""
    nodes = [
        RaftNodeState(node_id=node1, is_leader=True),
        RaftNodeState(node_id=node2, is_leader=True),
        RaftNodeState(node_id="node3", is_leader=False),
    ]
    context["cluster_state"] = RaftClusterState(nodes=nodes)


@given("a cluster where all 3 nodes claim leadership")
def cluster_all_leaders(context: dict):
    """Create a cluster where all nodes claim leadership."""
    nodes = [
        RaftNodeState(node_id="node1", is_leader=True),
        RaftNodeState(node_id="node2", is_leader=True),
        RaftNodeState(node_id="node3", is_leader=True),
    ]
    context["cluster_state"] = RaftClusterState(nodes=nodes)


@given("a SplitBrainStatus with is_split_brain true")
def split_brain_status_true(context: dict):
    """Create a SplitBrainStatus with is_split_brain=True."""
    leader_node = RaftNodeState(node_id="node1", is_leader=True)
    context["split_brain_status"] = SplitBrainStatus(
        is_split_brain=True,
        leader_nodes=[leader_node],
    )


# ---------------------------------------------------------------------------
# When steps - RaftNodeState
# ---------------------------------------------------------------------------


@when("I create a RaftNodeState with empty node_id")
def create_node_empty_id(context: dict):
    """Attempt to create RaftNodeState with empty node_id."""
    try:
        context["node_state"] = RaftNodeState(node_id="", is_leader=False)
        context["error"] = None
    except LiteFSConfigError as e:
        context["node_state"] = None
        context["error"] = e


@when("I create a RaftNodeState with whitespace-only node_id")
def create_node_whitespace_id(context: dict):
    """Attempt to create RaftNodeState with whitespace-only node_id."""
    try:
        context["node_state"] = RaftNodeState(node_id="   ", is_leader=False)
        context["error"] = None
    except LiteFSConfigError as e:
        context["node_state"] = None
        context["error"] = e


@when(
    parsers.parse(
        'I create a RaftNodeState with node_id "{node_id}" and is_leader {is_leader}'
    )
)
def create_node_valid(context: dict, node_id: str, is_leader: str):
    """Create a RaftNodeState with valid values."""
    try:
        context["node_state"] = RaftNodeState(
            node_id=node_id, is_leader=is_leader.lower() == "true"
        )
        context["error"] = None
    except LiteFSConfigError as e:
        context["node_state"] = None
        context["error"] = e


# ---------------------------------------------------------------------------
# When steps - RaftClusterState
# ---------------------------------------------------------------------------


@when("I create a RaftClusterState with empty nodes list")
def create_cluster_empty_nodes(context: dict):
    """Attempt to create RaftClusterState with empty nodes list."""
    try:
        context["cluster_state"] = RaftClusterState(nodes=[])
        context["error"] = None
    except LiteFSConfigError as e:
        context["cluster_state"] = None
        context["error"] = e


# ---------------------------------------------------------------------------
# When steps - SplitBrainDetector
# ---------------------------------------------------------------------------


@when("I check for split-brain")
def check_split_brain(context: dict):
    """Execute split-brain detection."""
    cluster_state = context["cluster_state"]
    port = FakeSplitBrainDetectorPort(cluster_state)
    detector = SplitBrainDetector(port=port)
    context["result"] = detector.detect_split_brain()


@when("I attempt to modify is_split_brain")
def attempt_modify_split_brain_status(context: dict):
    """Attempt to modify the frozen SplitBrainStatus."""
    status = context["split_brain_status"]
    try:
        status.is_split_brain = False  # type: ignore
        context["error"] = None
    except FrozenInstanceError as e:
        context["error"] = e


# ---------------------------------------------------------------------------
# Then steps - Errors
# ---------------------------------------------------------------------------


@then("a LiteFSConfigError should be raised")
def config_error_raised(context: dict):
    """Assert that LiteFSConfigError was raised."""
    assert (
        context["error"] is not None
    ), "Expected LiteFSConfigError but no error was raised"
    assert isinstance(context["error"], LiteFSConfigError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(context: dict, text: str):
    """Assert error message contains expected text."""
    assert context["error"] is not None
    assert text in str(context["error"]), f"Expected '{text}' in '{context['error']}'"


@then("a FrozenInstanceError should be raised")
def frozen_error_raised(context: dict):
    """Assert that FrozenInstanceError was raised."""
    assert (
        context["error"] is not None
    ), "Expected FrozenInstanceError but no error was raised"
    assert isinstance(context["error"], FrozenInstanceError)


# ---------------------------------------------------------------------------
# Then steps - RaftNodeState
# ---------------------------------------------------------------------------


@then("the RaftNodeState should be valid")
def node_state_valid(context: dict):
    """Assert RaftNodeState was created successfully."""
    assert context.get("error") is None, f"Unexpected error: {context.get('error')}"
    assert context["node_state"] is not None


@then(parsers.parse('the node_id should be "{expected}"'))
def node_id_is(context: dict, expected: str):
    """Assert node_id matches expected value."""
    assert context["node_state"].node_id == expected


@then(parsers.parse("is_leader should be {expected}"))
def is_leader_is(context: dict, expected: str):
    """Assert is_leader matches expected value."""
    expected_bool = expected.lower() == "true"
    assert context["node_state"].is_leader == expected_bool


# ---------------------------------------------------------------------------
# Then steps - RaftClusterState
# ---------------------------------------------------------------------------


@then("the RaftClusterState should be valid")
def cluster_state_valid(context: dict):
    """Assert RaftClusterState was created successfully."""
    assert context.get("error") is None, f"Unexpected error: {context.get('error')}"
    assert context["cluster_state"] is not None


@then(parsers.parse("count_leaders should return {expected:d}"))
def count_leaders_is(context: dict, expected: int):
    """Assert count_leaders returns expected value."""
    cluster = context["cluster_state"]
    assert cluster.count_leaders() == expected


@then(parsers.parse("has_single_leader should be {expected}"))
def has_single_leader_is(context: dict, expected: str):
    """Assert has_single_leader matches expected value."""
    expected_bool = expected.lower() == "true"
    cluster = context["cluster_state"]
    assert cluster.has_single_leader() == expected_bool


@then(parsers.parse('get_leader_nodes should return nodes "{node1}" and "{node2}"'))
def get_leader_nodes_are(context: dict, node1: str, node2: str):
    """Assert get_leader_nodes returns expected nodes."""
    cluster = context["cluster_state"]
    leader_nodes = cluster.get_leader_nodes()
    leader_ids = {node.node_id for node in leader_nodes}
    assert leader_ids == {node1, node2}


# ---------------------------------------------------------------------------
# Then steps - SplitBrainDetector
# ---------------------------------------------------------------------------


@then(parsers.parse("is_split_brain should be {expected}"))
def is_split_brain_is(context: dict, expected: str):
    """Assert is_split_brain matches expected value."""
    expected_bool = expected.lower() == "true"
    result = context["result"]
    assert result.is_split_brain == expected_bool


@then(parsers.parse("leader_nodes should contain {expected:d} node"))
def leader_nodes_count_singular(context: dict, expected: int):
    """Assert leader_nodes contains expected number of nodes (singular)."""
    result = context["result"]
    assert len(result.leader_nodes) == expected


@then(parsers.parse("leader_nodes should contain {expected:d} nodes"))
def leader_nodes_count(context: dict, expected: int):
    """Assert leader_nodes contains expected number of nodes."""
    result = context["result"]
    assert len(result.leader_nodes) == expected


@then("leader_nodes should be empty")
def leader_nodes_empty(context: dict):
    """Assert leader_nodes is empty."""
    result = context["result"]
    assert len(result.leader_nodes) == 0
