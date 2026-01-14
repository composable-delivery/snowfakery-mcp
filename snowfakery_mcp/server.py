from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.prompts import register_prompts
from snowfakery_mcp.resources.discovery import register_discovery_resources
from snowfakery_mcp.resources.runs import register_run_resources
from snowfakery_mcp.resources.static import register_static_resources
from snowfakery_mcp.tools.analyze import register_analyze_tool
from snowfakery_mcp.tools.capabilities import register_capabilities_tools
from snowfakery_mcp.tools.docs import register_doc_tools
from snowfakery_mcp.tools.examples import register_example_tools
from snowfakery_mcp.tools.mapping import register_mapping_tool
from snowfakery_mcp.tools.run import register_run_tool
from snowfakery_mcp.tools.validate import register_validate_tool


def create_app() -> FastMCP:
    paths = WorkspacePaths.detect()
    config = Config.from_env()

    app = FastMCP("snowfakery-mcp")

    register_static_resources(app, paths)
    register_discovery_resources(app)
    register_run_resources(app, paths)

    register_capabilities_tools(app, config)
    register_example_tools(app, paths)
    register_doc_tools(app, paths)
    register_validate_tool(app, paths, config)
    register_analyze_tool(app, paths)
    register_run_tool(app, paths, config)
    register_mapping_tool(app, paths, config)

    register_prompts(app)

    return app


mcp: FastMCP = create_app()


def run() -> None:
    mcp.run()
