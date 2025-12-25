"""Unit tests for port interfaces and default implementations."""

import os
import socket
import pytest

from litefs.adapters.ports import NodeIDResolverPort, EnvironmentNodeIDResolver


@pytest.mark.unit
class TestNodeIDResolverPort:
    """Test NodeIDResolverPort protocol interface."""

    def test_protocol_has_resolve_node_id_method(self) -> None:
        """Test that NodeIDResolverPort has resolve_node_id method."""
        assert hasattr(NodeIDResolverPort, "resolve_node_id")

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that NodeIDResolverPort is runtime_checkable."""
        # Create a simple object that implements the protocol
        class FakeResolver:
            def resolve_node_id(self) -> str:
                return "fake-node"

        fake = FakeResolver()
        # If runtime_checkable works, isinstance should return True
        assert isinstance(fake, NodeIDResolverPort)


@pytest.mark.unit
class TestEnvironmentNodeIDResolver:
    """Test EnvironmentNodeIDResolver implementation."""

    def test_resolve_from_environment_variable(self) -> None:
        """Test resolving node ID from LITEFS_NODE_ID environment variable."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-1"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_resolve_with_fqdn_hostname(self) -> None:
        """Test resolving FQDN hostname from environment."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "app-server-01.example.com"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "app-server-01.example.com"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_raise_on_missing_environment_variable(self) -> None:
        """Test that KeyError is raised when LITEFS_NODE_ID is not set."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ.pop("LITEFS_NODE_ID", None)
            resolver = EnvironmentNodeIDResolver()
            with pytest.raises(KeyError, match="LITEFS_NODE_ID"):
                resolver.resolve_node_id()
        finally:
            if original is not None:
                os.environ["LITEFS_NODE_ID"] = original

    def test_strips_leading_whitespace(self) -> None:
        """Test that leading whitespace is stripped from node ID."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "  node-1"
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_strips_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is stripped from node ID."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-1  "
            resolver = EnvironmentNodeIDResolver()
            assert resolver.resolve_node_id() == "node-1"
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_rejects_whitespace_only_value(self) -> None:
        """Test that whitespace-only node ID is rejected."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "   "
            resolver = EnvironmentNodeIDResolver()
            with pytest.raises(ValueError, match="node ID cannot be empty"):
                resolver.resolve_node_id()
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_satisfies_protocol(self) -> None:
        """Test that EnvironmentNodeIDResolver satisfies NodeIDResolverPort protocol."""
        resolver = EnvironmentNodeIDResolver()
        assert isinstance(resolver, NodeIDResolverPort)


@pytest.mark.unit
class TestProtocolImplementationContract:
    """Test contract between protocol and implementations."""

    def test_environment_resolver_returns_string(self) -> None:
        """Test that EnvironmentNodeIDResolver.resolve_node_id() returns str."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "test-node"
            resolver = EnvironmentNodeIDResolver()
            result = resolver.resolve_node_id()
            assert isinstance(result, str)
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original

    def test_environment_resolver_never_returns_empty_string(self) -> None:
        """Test that resolve_node_id() never returns empty string."""
        original = os.environ.get("LITEFS_NODE_ID")
        try:
            os.environ["LITEFS_NODE_ID"] = "node-123"
            resolver = EnvironmentNodeIDResolver()
            result = resolver.resolve_node_id()
            assert result != ""
            assert len(result) > 0
        finally:
            if original is None:
                os.environ.pop("LITEFS_NODE_ID", None)
            else:
                os.environ["LITEFS_NODE_ID"] = original
