"""Tests for server initialization and app creation."""

from __future__ import annotations

from snowfakery_mcp.server import create_app


class TestCreateApp:
    """Test MCP server app creation."""

    def test_create_app_returns_instance(self) -> None:
        """Test that create_app returns an app instance."""
        app = create_app()
        assert app is not None

    def test_create_app_idempotent(self) -> None:
        """Test that create_app can be called multiple times."""
        app1 = create_app()
        app2 = create_app()

        # Both should be valid instances
        assert app1 is not None
        assert app2 is not None
