"""Snowfakery MCP Server - Built on FastMCP.

This server provides tools, resources, and prompts for authoring, analyzing,
debugging, and running Snowfakery recipes via the Model Context Protocol (MCP).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.prompts import register_prompts
from snowfakery_mcp.resources.discovery import register_discovery_resources
from snowfakery_mcp.resources.runs import register_run_resources
from snowfakery_mcp.resources.static import register_static_resources
from snowfakery_mcp.resources.templates import register_template_resources
from snowfakery_mcp.tools.agentic import register_agentic_tools
from snowfakery_mcp.tools.analyze import register_analyze_tool
from snowfakery_mcp.tools.capabilities import register_capabilities_tools
from snowfakery_mcp.tools.docs import register_doc_tools
from snowfakery_mcp.tools.examples import register_example_tools
from snowfakery_mcp.tools.mapping import register_mapping_tool
from snowfakery_mcp.tools.run import register_run_tool
from snowfakery_mcp.tools.validate import register_validate_tool


def create_app() -> FastMCP:
    """Create and configure the Snowfakery MCP server."""

    # Single source of truth for Config, computed exactly once. Every
    # registered tool/resource/prompt below reads paths/config from
    # ``ctx.lifespan_context`` at call time (populated by the nested
    # ``lifespan`` below) instead of closing over registration-time values -
    # replacing the old create_app()/lifespan() split-brain (two independently
    # constructed WorkspacePaths/Config, one of which - the module-level
    # ``_ServerState`` - nothing ever read).
    #
    # The one deliberate exception: ``@mcp.tool(timeout=...)`` (Phase 5) is
    # resolved at decoration time, before any lifespan/request context exists,
    # so it structurally cannot be sourced from ``ctx.lifespan_context``. The
    # four tools that call ``generate_data()`` (run_recipe, generate_mapping,
    # validate_recipe, iterative_recipe_gen) take this plain pre-lifespan
    # scalar directly into their ``register_*`` function - sourced from this
    # same single ``Config.from_env()`` call, not a second independently
    # constructed ``Config`` - so Phase 5 has an already-anticipated slot to
    # pass straight into ``@mcp.tool(timeout=timeout_seconds)``.
    config = Config.from_env()
    timeout_seconds = config.timeout_seconds

    @asynccontextmanager
    async def lifespan(_app: FastMCP) -> AsyncIterator[dict[str, Any]]:
        """Server lifespan manager - runs once per server instance.

        Yields the single ``{"paths": ..., "config": ...}`` dict that every
        tool/resource/prompt reads via ``ctx.lifespan_context``. Closes over
        the single ``config`` computed above rather than calling
        ``Config.from_env()`` a second time; ``WorkspacePaths.detect()`` only
        needs to run here, since nothing at registration time reads it
        anymore.
        """
        paths = WorkspacePaths.detect()

        # Ensure runs directory exists
        paths.runs_root()

        yield {"paths": paths, "config": config}

    app = FastMCP(
        name="snowfakery-mcp",
        instructions="""
        Snowfakery MCP Server - Generate realistic fake data with relationships.

        Available capabilities:
        - Use list_capabilities to see all server features and limits
        - Use list_examples to browse example recipes
        - Use get_example to fetch a specific example
        - Use validate_recipe to check recipe syntax
        - Use analyze_recipe to inspect recipe structure
        - Use run_recipe to generate data
        - Use generate_mapping to create CumulusCI mapping files
        - Use search_docs to search documentation
        - Use get_schema to get the JSON schema for recipes

        Resources available:
        - snowfakery://schema/recipe-jsonschema - Recipe JSON schema
        - snowfakery://docs/* - Documentation
        - snowfakery://examples/* - Example recipes
        - snowfakery://templates/* - Community recipe templates
        - snowfakery://providers/list - Available Faker providers
        - snowfakery://plugins/list - Available plugins
        - snowfakery://formats/info - Output format details
        - snowfakery://runs/{run_id}/* - Run artifacts

        Prompts available:
        - author_recipe - Help author a new recipe
        - debug_recipe - Help debug a failing recipe
        """,
        lifespan=lifespan,
    )

    # Outer backstop: catches any exception that escapes a tool/resource/prompt
    # handler entirely (e.g. one with no business-logic try/except of its own)
    # and turns it into a proper MCP error response instead of an unhandled
    # crash. Not a substitute for the ToolResult(is_error=...) business-logic
    # contract the execution tools use above their own try/except blocks.
    app.add_middleware(ErrorHandlingMiddleware())

    # Baseline observability (Phase 7): purely additive, zero tool-code
    # changes. Middleware is applied in registration order from the outside
    # in (i.e. ErrorHandlingMiddleware above wraps everything below), so
    # Logging wraps Timing wraps ResponseLimiting wraps the actual handler -
    # each per-call log line brackets the timing measurement, which in turn
    # brackets the (rare) response-truncation work closest to the tool call.
    #
    # Logging/timing both log through stdlib ``logging`` under the
    # ``fastmcp.*`` namespace, which ``fastmcp`` itself already configures
    # (on `import fastmcp`, see fastmcp.utilities.logging.configure_logging)
    # with a handler that explicitly targets stderr (rich Console(stderr=True)
    # or a plain logging.StreamHandler(), both stderr by default) - the same
    # reason Snowfakery's own progress output is safe on stdio transport,
    # since stdio reserves stdout exclusively for JSON-RPC. Verified directly
    # (not just assumed, per this phase's risk note) via a manual
    # `uv run snowfakery-mcp` stdio session with stdout/stderr captured
    # separately.
    app.add_middleware(LoggingMiddleware())
    app.add_middleware(TimingMiddleware())

    # Defense-in-depth output-size backstop for tools with no cap of their
    # own today (e.g. analyze_recipe, search_docs, list_examples/get_example)
    # - run_recipe/generate_mapping already truncate their captured-output
    # field to config.max_capture_chars before this ever sees it. Sized
    # generously above config.max_capture_chars (which itself is only a
    # single-field character cap, not a whole-response byte cap, and is
    # user-configurable up to 5_000_000 via SNOWFAKERY_MCP_MAX_CAPTURE_CHARS)
    # so this backstop never truncates a response that is merely large by
    # configuration - it should only trip for genuinely unbounded tools.
    response_limit_bytes = max(1_000_000, config.max_capture_chars * 10)
    app.add_middleware(ResponseLimitingMiddleware(max_size=response_limit_bytes))

    # Register static resources (schema, docs, examples)
    register_static_resources(app)
    register_template_resources(app)

    # Register discovery resources (providers, plugins, formats)
    register_discovery_resources(app)

    # Register run artifact resources
    register_run_resources(app)

    # Register tools
    register_capabilities_tools(app)
    register_example_tools(app)
    register_doc_tools(app)
    register_validate_tool(app, timeout_seconds=timeout_seconds)
    register_analyze_tool(app)
    register_run_tool(app, timeout_seconds=timeout_seconds)
    register_mapping_tool(app, timeout_seconds=timeout_seconds)
    register_agentic_tools(app, timeout_seconds=timeout_seconds)

    # Register prompts
    register_prompts(app)

    return app


# Create the server instance
mcp: FastMCP = create_app()


def run() -> None:
    """Run the MCP server (stdio transport by default)."""
    mcp.run()


if __name__ == "__main__":
    run()
