from __future__ import annotations

from io import StringIO
from typing import Any

from mcp.server.fastmcp import FastMCP
from snowfakery.api import generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import recipe_text_from_input
from snowfakery_mcp.core.timeout import OperationTimeout, time_limit
from snowfakery_mcp.core.types import ToolError, ValidateResult


def register_validate_tool(mcp: FastMCP, paths: WorkspacePaths, config: Config) -> None:
    @mcp.tool()
    def validate_recipe(
        *,
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        strict_mode: bool = True,
        schema_validate: bool = False,
        options: dict[str, Any] | None = None,
        plugin_options: dict[str, Any] | None = None,
    ) -> ValidateResult:
        """Validate a recipe using Snowfakery's validate-only mode.

        Note: schema_validate is reserved for adding JSON-schema validation later.
        """

        _ = schema_validate
        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        try:
            with time_limit(config.timeout_seconds):
                generate_data(
                    StringIO(text),
                    parent_application=MCPApplication(),
                    user_options=dict(options or {}),
                    plugin_options=dict(plugin_options or {}),
                    strict_mode=strict_mode,
                    validate_only=True,
                    output_format="txt",
                    output_files=[StringIO()],
                )
            return {"valid": True, "errors": []}
        except DataGenError as e:
            err: ToolError = {
                "kind": type(e).__name__,
                "message": e.message,
                "filename": e.filename,
                "line": e.line_num,
            }
            return {"valid": False, "errors": [err]}
        except OperationTimeout as e:
            timeout_err: ToolError = {
                "kind": type(e).__name__,
                "message": str(e),
                "filename": None,
                "line": None,
            }
            return {"valid": False, "errors": [timeout_err]}
        except Exception as e:
            # Snowfakery can raise non-DataGenError exceptions for some invalid inputs.
            unexpected: ToolError = {
                "kind": type(e).__name__,
                "message": str(e),
                "filename": None,
                "line": None,
            }
            return {"valid": False, "errors": [unexpected]}
