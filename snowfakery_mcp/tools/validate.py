from __future__ import annotations

from io import StringIO
from typing import Any

from fastmcp import FastMCP
from snowfakery.api import generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import recipe_text_from_input
from snowfakery_mcp.core.timeout import OperationTimeout, time_limit
from snowfakery_mcp.core.types import ToolError, ValidateResult


def register_validate_tool(mcp: FastMCP, paths: WorkspacePaths, config: Config) -> None:
    @mcp.tool(tags={"authoring", "validation"})
    def validate_recipe(
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        strict_mode: bool = True,
        schema_validate: bool = False,
        options: dict[str, Any] | None = None,
        plugin_options: dict[str, Any] | None = None,
    ) -> ValidateResult:
        """Validate a Snowfakery recipe without generating data.

        Checks recipe syntax and structure. Returns validation errors if any.
        Use either recipe_path (file on disk) or recipe_text (inline YAML).

        Args:
            recipe_path: Path to a recipe file (relative to workspace root)
            recipe_text: Recipe YAML content as a string
            strict_mode: If True, fail on undefined field references
            schema_validate: Reserved for future JSON schema validation
            options: User options to pass to the recipe
            plugin_options: Plugin-specific options
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
        except (OSError, RuntimeError, ValueError) as e:
            # Snowfakery can raise non-DataGenError exceptions for some invalid inputs.
            unexpected: ToolError = {
                "kind": type(e).__name__,
                "message": str(e),
                "filename": None,
                "line": None,
            }
            return {"valid": False, "errors": [unexpected]}
