from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from snowfakery.api import COUNT_REPS, generate_data, file_extensions
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import recipe_text_from_input, truncate
from snowfakery_mcp.core.types import RunResult, TargetNumber, ToolError


def _safe_stopping_criteria(
    *,
    config: Config,
    reps: Optional[int],
    target_number: Optional[TargetNumber],
) -> tuple[tuple[str, int] | None, Optional[int]]:
    if reps is not None and target_number is not None:
        raise ValueError("Provide only one of reps or target_number")

    if reps is None and target_number is None:
        reps = 1

    if reps is not None:
        if reps < 1:
            raise ValueError("reps must be >= 1")
        if reps > config.max_reps:
            raise ValueError(f"reps exceeds server limit ({config.max_reps})")
        return (COUNT_REPS, int(reps)), int(reps)

    assert target_number is not None
    table = target_number.get("table")
    count = target_number.get("count")
    if not isinstance(table, str) or not table:
        raise ValueError("target_number.table must be a non-empty string")
    if not isinstance(count, int) or count < 1:
        raise ValueError("target_number.count must be an int >= 1")
    if count > config.max_target_count:
        raise ValueError(f"target_number.count exceeds server limit ({config.max_target_count})")
    return (table, int(count)), None


def register_run_tool(mcp: FastMCP, paths: WorkspacePaths, config: Config) -> None:
    @mcp.tool()
    def run_recipe(
        *,
        recipe_path: Optional[str] = None,
        recipe_text: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
        plugin_options: Optional[dict[str, Any]] = None,
        reps: Optional[int] = None,
        target_number: Optional[TargetNumber] = None,
        output_format: str = "txt",
        capture_output: bool = True,
        strict_mode: bool = True,
        validate_only: bool = False,
        generate_continuation: bool = False,
    ) -> RunResult:
        """Run a Snowfakery recipe (or validate-only) and return captured output plus run artifacts."""

        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        run_id, run_dir = paths.new_run_dir()

        fmt = output_format.lower()
        if fmt not in set(file_extensions):
            raise ValueError(f"Unsupported output_format: {output_format}")

        target_tuple, _ = _safe_stopping_criteria(config=config, reps=reps, target_number=target_number)

        out_buf: Optional[StringIO] = None
        if capture_output and fmt in {"txt", "json", "sql", "dot", "svg", "svgz"}:
            out_buf = StringIO()

        artifact_name = f"output.{fmt}"
        artifact_path = run_dir / artifact_name

        output_files: list[Any] = []
        if out_buf is not None:
            output_files.append(out_buf)
        output_files.append(str(artifact_path))

        output_folder: Optional[str] = None
        if fmt == "csv":
            csv_dir = run_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)
            output_folder = str(csv_dir)
            output_files = []

        continuation_path: Optional[str] = None
        if generate_continuation:
            continuation_path = str(run_dir / "continuation.yml")

        try:
            summary = generate_data(
                StringIO(text),
                parent_application=MCPApplication(),
                user_options=dict(options or {}),
                plugin_options=dict(plugin_options or {}),
                target_number=target_tuple,
                output_format=fmt,
                output_files=output_files or None,
                output_folder=output_folder,
                strict_mode=strict_mode,
                validate_only=validate_only,
                generate_continuation_file=continuation_path,
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

        captured = out_buf.getvalue() if out_buf is not None else ""
        captured, truncated_flag = truncate(captured, max_chars=config.max_capture_chars)

        resources: list[str] = []
        if artifact_path.exists():
            resources.append(f"snowfakery://runs/{run_id}/{artifact_name}")
        if fmt == "csv":
            resources.append(f"snowfakery://runs/{run_id}/csv")
        if generate_continuation and continuation_path is not None:
            resources.append(f"snowfakery://runs/{run_id}/continuation.yml")

        return {
            "run_id": run_id,
            "ok": True,
            "output_format": fmt,
            "stdout_text": captured,
            "stdout_truncated": truncated_flag,
            "resources": resources,
            "summary": str(summary),
        }
