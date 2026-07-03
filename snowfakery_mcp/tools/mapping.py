from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import ToolAnnotations
from snowfakery.api import COUNT_REPS, generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.errors import tool_error_from_exception
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import read_text_utf8, recipe_text_from_input, truncate
from snowfakery_mcp.core.types import MappingResult, tool_output_schema

_OUTPUT_SCHEMA = tool_output_schema(MappingResult)


def register_mapping_tool(mcp: FastMCP, timeout_seconds: int) -> None:
    """Register ``generate_mapping``.

    ``timeout_seconds`` is the Phase-4 pre-lifespan carve-out (see
    ``server.create_app()``): ``@mcp.tool(timeout=...)`` is resolved at
    decoration time, before any lifespan/request context exists, so it can't
    be sourced from ``ctx.lifespan_context`` the way ``paths``/``config`` are
    below. Phase 5 passes it straight to ``@mcp.tool(timeout=timeout_seconds)``,
    replacing the old SIGALRM-based ``time_limit()`` call that used to wrap
    ``generate_data()`` below.

    Same honest caveat as ``tools/run.py``'s ``run_recipe`` (see its
    docstring): ``generate_mapping`` is a plain ``def`` dispatched to a
    worker thread, so ``timeout=`` does not actually bound wall-clock time
    for a stuck ``generate_data()`` call here either — verified against the
    installed fastmcp 3.4.2, not assumed.
    """

    @mcp.tool(
        tags={"execution", "salesforce"},
        output_schema=_OUTPUT_SCHEMA,
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False),
        timeout=timeout_seconds,
        version="1",
    )
    def generate_mapping(
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        load_declarations_paths: list[str] | None = None,
        *,
        ctx: Context,
    ) -> MappingResult | ToolResult:
        """Generate a CumulusCI mapping.yml file from a Snowfakery recipe.

        Creates the mapping file needed to load Snowfakery-generated data into
        Salesforce using CumulusCI. Returns a preview and artifact URI.

        Args:
            recipe_path: Path to recipe file (relative to workspace)
            recipe_text: Recipe YAML content as string
            load_declarations_paths: Optional paths to load declaration files
        """

        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        config: Config = ctx.lifespan_context["config"]

        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        run_id, run_dir = paths.new_run_dir()
        mapping_path = run_dir / "mapping.yml"

        try:
            declarations = [
                str(
                    paths.ensure_within_workspace(
                        (paths.root / p) if not Path(p).is_absolute() else Path(p)
                    )
                )
                for p in (load_declarations_paths or [])
            ]

            kwargs: dict[str, Any] = {
                "parent_application": MCPApplication(),
                "target_number": (COUNT_REPS, 1),
                "output_format": "txt",
                "output_files": [StringIO()],
                "generate_cci_mapping_file": str(mapping_path),
                "strict_mode": True,
                "validate_only": False,
            }
            if declarations:
                kwargs["load_declarations"] = declarations
            generate_data(StringIO(text), **kwargs)
        except (DataGenError, OSError, RuntimeError, ValueError) as e:
            err = tool_error_from_exception(e)
            return ToolResult(
                structured_content={
                    "run_id": run_id,
                    "ok": False,
                    "error": err,
                    "resources": [],
                },
                is_error=True,
            )

        mapping_text = read_text_utf8(mapping_path) if mapping_path.exists() else ""
        preview, truncated_flag = truncate(mapping_text, max_chars=config.max_capture_chars)

        return {
            "run_id": run_id,
            "ok": True,
            "mapping_preview": preview,
            "mapping_truncated": truncated_flag,
            "resources": [f"snowfakery://runs/{run_id}/mapping.yml"],
        }
