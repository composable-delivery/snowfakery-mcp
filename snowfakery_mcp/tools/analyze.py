from __future__ import annotations

from io import StringIO

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import ToolAnnotations
from snowfakery.data_gen_exceptions import DataGenError
from snowfakery.parse_recipe_yaml import parse_recipe

from snowfakery_mcp.core.errors import tool_error_from_exception
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import recipe_text_from_input
from snowfakery_mcp.core.types import AnalyzeRandomReference, AnalyzeResult, AnalyzeTableInfo


def register_analyze_tool(mcp: FastMCP) -> None:
    @mcp.tool(
        tags={"authoring", "analysis"},
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        version="1",
    )
    def analyze_recipe(
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        *,
        ctx: Context,
    ) -> AnalyzeResult | ToolResult:
        """Parse and analyze a Snowfakery recipe structure.

        Returns structural information about the recipe including:
        - Tables and their fields
        - Declared plugins and options
        - Random reference usage
        - Recipe version

        Use this before running to understand recipe structure.
        """

        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        try:
            pr = parse_recipe(StringIO(text))
        except (DataGenError, OSError, RuntimeError, ValueError) as e:
            err = tool_error_from_exception(e)
            return ToolResult(structured_content={"error": err}, is_error=True)

        tables: dict[str, AnalyzeTableInfo] = {}
        for name, info in pr.tables.items():
            tables[name] = {
                "fields": sorted(info.fields.keys()),
                "friends": sorted(info.friends.keys()),
                "has_update_keys": bool(getattr(info, "has_update_keys", False)),
            }

        uses_random_reference: list[AnalyzeRandomReference] = [
            {
                "function": getattr(rr, "function_name", None),
                "line": getattr(rr, "line_num", None),
                "filename": getattr(rr, "filename", None),
            }
            for rr in (pr.random_references or [])
        ]

        return {
            "version": pr.version,
            "plugins_declared": [str(p) for p in (pr.plugins or [])],
            "options_declared": [str(o) for o in (pr.options or [])],
            "tables": tables,
            "uses_random_reference": uses_random_reference,
        }
