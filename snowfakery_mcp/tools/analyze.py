from __future__ import annotations

from io import StringIO
from typing import Any

from mcp.server.fastmcp import FastMCP
from snowfakery.parse_recipe_yaml import parse_recipe

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import recipe_text_from_input


def register_analyze_tool(mcp: FastMCP, paths: WorkspacePaths) -> None:
    @mcp.tool()
    def analyze_recipe(
        *,
        recipe_path: str | None = None,
        recipe_text: str | None = None,
    ) -> dict[str, Any]:
        """Parse a recipe and return a structural summary (tables, fields, options, plugins)."""

        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        pr = parse_recipe(StringIO(text))

        tables: dict[str, Any] = {}
        for name, info in pr.tables.items():
            tables[name] = {
                "fields": sorted(info.fields.keys()),
                "friends": sorted(info.friends.keys()),
                "has_update_keys": bool(getattr(info, "has_update_keys", False)),
            }

        return {
            "version": pr.version,
            "plugins_declared": [str(p) for p in (pr.plugins or [])],
            "options_declared": [str(o) for o in (pr.options or [])],
            "tables": tables,
            "uses_random_reference": [
                {
                    "function": getattr(rr, "function_name", None),
                    "line": getattr(rr, "line_num", None),
                    "filename": getattr(rr, "filename", None),
                }
                for rr in (pr.random_references or [])
            ],
        }
