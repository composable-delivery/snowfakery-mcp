from __future__ import annotations

from io import StringIO
from typing import Any

from fastmcp.tools import ToolResult
from snowfakery.api import generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.errors import tool_error_from_exception
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import recipe_text_from_input
from snowfakery_mcp.core.types import ValidateResult


def validate_recipe_logic(
    paths: WorkspacePaths,
    config: Config,
    recipe_path: str | None = None,
    recipe_text: str | None = None,
    strict_mode: bool = True,
    options: dict[str, Any] | None = None,
    plugin_options: dict[str, Any] | None = None,
) -> ValidateResult | ToolResult:
    """Core logic for validating a recipe.

    ``config`` is kept in the signature for both call sites
    (``tools/validate.py``'s ``validate_recipe`` and ``tools/agentic.py``'s
    ``iterative_recipe_gen`` loop) even though, as of Phase 5, nothing in
    this function reads it anymore: the SIGALRM-based ``time_limit()`` call
    that used to consume ``config.timeout_seconds`` here is gone, replaced
    by each *caller's own* ``@mcp.tool(timeout=timeout_seconds)`` (see
    FASTMCP3_REFACTOR_PLAN.md Phase 5).
    """
    text = recipe_text_from_input(
        recipe_path=recipe_path,
        recipe_text=recipe_text,
        workspace_root=paths.root,
    )

    try:
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
    except (DataGenError, OSError, RuntimeError, ValueError) as e:
        err = tool_error_from_exception(e)
        return ToolResult(
            structured_content={"valid": False, "errors": [err]},
            is_error=True,
        )
