from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from snowfakery.api import COUNT_REPS, generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import recipe_text_from_input, read_text_utf8, truncate
from snowfakery_mcp.core.types import ToolError


def register_mapping_tool(mcp: FastMCP, paths: WorkspacePaths, config: Config) -> None:
    @mcp.tool()
    def generate_mapping(
        *,
        recipe_path: Optional[str] = None,
        recipe_text: Optional[str] = None,
        load_declarations_paths: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Generate a CumulusCI mapping.yml for a recipe and return a preview plus run artifact URI."""

        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        run_id, run_dir = paths.new_run_dir()
        mapping_path = run_dir / "mapping.yml"

        try:
            declarations = [
                str(paths.ensure_within_workspace((paths.root / p) if not Path(p).is_absolute() else Path(p)))
                for p in (load_declarations_paths or [])
            ]

            generate_data(
                StringIO(text),
                parent_application=MCPApplication(),
                target_number=(COUNT_REPS, 1),
                output_format="txt",
                output_files=[StringIO()],
                generate_cci_mapping_file=str(mapping_path),
                load_declarations=declarations or None,
                strict_mode=True,
                validate_only=False,
            )
        except DataGenError as e:
            err: ToolError = {
                "kind": type(e).__name__,
                "message": e.message,
                "filename": e.filename,
                "line": e.line_num,
            }
            return {"run_id": run_id, "ok": False, "error": err, "resources": []}
        except Exception as e:
            unexpected: ToolError = {
                "kind": type(e).__name__,
                "message": str(e),
                "filename": None,
                "line": None,
            }
            return {"run_id": run_id, "ok": False, "error": unexpected, "resources": []}

        mapping_text = read_text_utf8(mapping_path) if mapping_path.exists() else ""
        preview, truncated_flag = truncate(mapping_text, max_chars=config.max_capture_chars)

        return {
            "run_id": run_id,
            "ok": True,
            "mapping_preview": preview,
            "mapping_truncated": truncated_flag,
            "resources": [f"snowfakery://runs/{run_id}/mapping.yml"],
        }
