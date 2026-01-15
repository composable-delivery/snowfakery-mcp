from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.types import ValidateResult
from snowfakery_mcp.core.validate import validate_recipe_logic


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
        return validate_recipe_logic(
            paths=paths,
            config=config,
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            strict_mode=strict_mode,
            options=options,
            plugin_options=plugin_options,
        )
