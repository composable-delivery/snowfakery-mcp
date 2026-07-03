from __future__ import annotations

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from snowfakery.__about__ import __version__ as snowfakery_version
from snowfakery.api import file_extensions

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.types import CapabilitiesResult


def register_capabilities_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        tags={"discovery", "info"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        version="1",
    )
    def list_capabilities(ctx: Context) -> CapabilitiesResult:
        """Return Snowfakery + server capability info.

        Use this tool first to understand what the server can do, including:
        - Snowfakery version
        - Supported output formats
        - Server limits (timeout, max output, max reps)
        - Available resources
        """

        config: Config = ctx.lifespan_context["config"]

        return {
            "snowfakery_version": snowfakery_version,
            "supported_output_formats": list(file_extensions),
            # Previously duplicated verbatim as four top-level scalar fields
            # *and* this nested "limits" dict (Phase 6 fixes the duplication;
            # see FASTMCP3_REFACTOR_PLAN.md Phase 6, step 2) - "limits" is now
            # the single source of truth.
            "limits": {
                "timeout_seconds": config.timeout_seconds,
                "max_capture_chars": config.max_capture_chars,
                "preview_chars": config.preview_chars,
                "max_reps": config.max_reps,
                "max_target_count": config.max_target_count,
            },
            "resources": {
                "schema": "snowfakery://schema/recipe-jsonschema",
                "docs": [
                    "snowfakery://docs/index",
                    "snowfakery://docs/extending",
                    "snowfakery://docs/salesforce",
                    "snowfakery://docs/architecture",
                ],
                "examples": "snowfakery://examples/list",
            },
        }
