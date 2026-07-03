"""Tests for server initialization and app creation."""

from __future__ import annotations

import textwrap
from typing import Any

import pytest
from fastmcp import Client, Context
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
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


@pytest.mark.anyio
async def test_lifespan_context_has_paths_and_config() -> None:
    """Regression test for the create_app()/lifespan() split-brain fix (Phase 4).

    Every registered tool/resource now reads paths/config from
    ``ctx.lifespan_context`` at call time, populated by a single
    lifespan-yielded dict - replacing the old setup where create_app() and
    lifespan() each independently constructed their own WorkspacePaths/Config
    (one set baked into registration-time closures, the other stashed in the
    now-deleted ``_ServerState`` that nothing ever read). Uses a fresh
    create_app() instance (not the shared server_app singleton) with one
    throwaway probe tool, so it doesn't leak extra tools into other tests
    driving the shared ``mcp_client`` fixture.
    """
    app = create_app()
    seen: dict[str, Any] = {}

    @app.tool
    def _lifespan_probe(ctx: Context) -> list[str]:
        seen.update(ctx.lifespan_context)
        return sorted(ctx.lifespan_context.keys())

    async with Client(app) as client:
        result = await client.call_tool("_lifespan_probe", {})

    assert result.data == ["config", "paths"]
    assert isinstance(seen["paths"], WorkspacePaths)
    assert isinstance(seen["config"], Config)


def test_create_app_registers_baseline_observability_middleware() -> None:
    """Regression test for Phase 7: LoggingMiddleware/TimingMiddleware/
    ResponseLimitingMiddleware must all be registered on the app returned by
    create_app(), alongside the pre-existing ErrorHandlingMiddleware backstop
    (Phase 3), so a future accidental removal is caught explicitly rather than
    only showing up as a loss of log output nobody notices."""
    app = create_app()

    middleware_types = [type(mw) for mw in app.middleware]

    assert ErrorHandlingMiddleware in middleware_types
    assert LoggingMiddleware in middleware_types
    assert TimingMiddleware in middleware_types
    assert ResponseLimitingMiddleware in middleware_types

    # Registration order determines nesting: earlier-registered middleware
    # wraps later-registered middleware (fastmcp's ``FastMCP._run_middleware``
    # builds the chain by iterating ``reversed(self.middleware)``). Assert
    # ErrorHandlingMiddleware stays outermost relative to the Phase 7
    # additions - it must be able to catch exceptions escaping the
    # observability middleware too, not just tool handlers - and that
    # ResponseLimitingMiddleware stays innermost (closest to the actual
    # tool call) so its size measurement reflects the real response, not
    # something already rewritten by an earlier middleware layer. (Not
    # asserting index 0 overall: FastMCP itself auto-registers a
    # DereferenceRefsMiddleware ahead of anything this server adds.)
    assert middleware_types.index(ErrorHandlingMiddleware) < middleware_types.index(
        LoggingMiddleware
    )
    assert middleware_types.index(LoggingMiddleware) < middleware_types.index(TimingMiddleware)
    assert middleware_types.index(TimingMiddleware) < middleware_types.index(
        ResponseLimitingMiddleware
    )


@pytest.mark.anyio
async def test_run_recipe_structured_content_unchanged_with_middleware(
    mcp_client: Client[Any],
) -> None:
    """Smoke test (Phase 7 testing strategy): a normal run_recipe call must
    still return identical structured content now that LoggingMiddleware/
    TimingMiddleware/ResponseLimitingMiddleware are installed - this phase is
    purely additive/observational and must not alter any tool's wire
    payload."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 1
          fields:
            name: TestUser
        """
    ).strip()

    result = await mcp_client.call_tool(
        "run_recipe",
        {"recipe_text": recipe, "reps": 1, "output_format": "txt"},
    )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["ok"] is True
    assert result.structured_content["run_id"]
