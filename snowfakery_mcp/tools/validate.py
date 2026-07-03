from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import ToolAnnotations

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.types import ValidateResult, tool_output_schema
from snowfakery_mcp.core.validate import validate_recipe_logic


def register_validate_tool(mcp: FastMCP, timeout_seconds: int) -> None:
    """Register ``validate_recipe``.

    ``timeout_seconds`` is the Phase-4 pre-lifespan carve-out (see
    ``server.create_app()``): ``@mcp.tool(timeout=...)`` is resolved at
    decoration time, before any lifespan/request context exists. Phase 5
    wires it straight into the decorator below, replacing the old
    SIGALRM-based ``time_limit()`` call that used to live inside
    ``validate_recipe_logic()``.

    Same honest caveat as ``run_recipe``/``generate_mapping`` (see
    ``tools/run.py``'s docstring): ``validate_recipe`` is a plain ``def``
    dispatched to a worker thread, so ``timeout=`` does not actually bound
    wall-clock time for a stuck ``generate_data()`` call underneath it.
    """

    @mcp.tool(
        tags={"authoring", "validation"},
        output_schema=tool_output_schema(ValidateResult),
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        timeout=timeout_seconds,
        version="1",
    )
    def validate_recipe(
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        strict_mode: bool = True,
        schema_validate: bool = False,
        options: dict[str, Any] | None = None,
        plugin_options: dict[str, Any] | None = None,
        *,
        ctx: Context,
    ) -> ValidateResult | ToolResult:
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
        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        config: Config = ctx.lifespan_context["config"]
        return validate_recipe_logic(
            paths=paths,
            config=config,
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            strict_mode=strict_mode,
            options=options,
            plugin_options=plugin_options,
        )
