"""Snowfakery MCP Server - Built on FastMCP.

This server provides tools, resources, and prompts for authoring, analyzing,
debugging, and running Snowfakery recipes via the Model Context Protocol (MCP).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastmcp import FastMCP

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

if TYPE_CHECKING:
    pass


class _ServerState:
    """Module-level server state."""

    paths: WorkspacePaths | None = None
    config: Config | None = None


def get_paths() -> WorkspacePaths:
    """Get the current WorkspacePaths instance (available after server startup)."""
    if _ServerState.paths is None:
        raise RuntimeError("Server not initialized - paths not available")
    return _ServerState.paths


def get_config() -> Config:
    """Get the current Config instance (available after server startup)."""
    if _ServerState.config is None:
        raise RuntimeError("Server not initialized - config not available")
    return _ServerState.config


@asynccontextmanager
async def lifespan(_app: FastMCP) -> AsyncIterator[None]:
    """Server lifespan manager - runs once per server instance.

    This is the proper place to initialize expensive resources like:
    - Database connections
    - Configuration loading
    - Background task setup
    - Workspace detection
    """
    # Startup: Initialize paths and config
    _ServerState.paths = WorkspacePaths.detect()
    _ServerState.config = Config.from_env()

    # Ensure runs directory exists
    _ServerState.paths.runs_root()

    yield

    # Cleanup (if needed in the future)
    _paths = None
    _config = None


def create_app() -> FastMCP:
    """Create and configure the Snowfakery MCP server."""

    # Pre-initialize paths and config for registration (lifespan will re-init at runtime)
    paths = WorkspacePaths.detect()
    config = Config.from_env()

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

    # Register static resources (schema, docs, examples)
    register_static_resources(app, paths)
    register_template_resources(app, paths)

    # Register discovery resources (providers, plugins, formats)
    register_discovery_resources(app)

    # Register run artifact resources
    register_run_resources(app, paths)

    # Register tools
    register_capabilities_tools(app, config)
    register_example_tools(app, paths)
    register_doc_tools(app, paths)
    register_validate_tool(app, paths, config)
    register_analyze_tool(app, paths)
    register_run_tool(app, paths, config)
    register_mapping_tool(app, paths, config)
    register_agentic_tools(app, paths, config)

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
