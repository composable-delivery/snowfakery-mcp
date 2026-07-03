from __future__ import annotations

from io import StringIO
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import ToolAnnotations
from snowfakery.api import COUNT_REPS, file_extensions, generate_data
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.errors import tool_error_from_exception
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.snowfakery_app import MCPApplication
from snowfakery_mcp.core.text import read_text_utf8, recipe_text_from_input, smart_truncate_output
from snowfakery_mcp.core.types import RunResult, TargetNumber, tool_output_schema

CaptureMode = Literal["preview", "full", "none"]


def _safe_stopping_criteria(
    config: Config,
    reps: int | None,
    target_number: TargetNumber | None,
) -> tuple[tuple[str, int] | None, int | None]:
    if reps is not None and target_number is not None:
        raise ValueError("Provide only one of reps or target_number")

    if reps is None and target_number is None:
        reps = 1

    if reps is not None:
        if reps < 1:
            raise ValueError("reps must be >= 1")
        if reps > config.max_reps:
            raise ValueError(f"reps exceeds server limit ({config.max_reps})")
        return (COUNT_REPS, reps), reps

    assert target_number is not None
    table = target_number.get("table")
    count = target_number.get("count")
    if not isinstance(table, str) or not table:
        raise ValueError("target_number.table must be a non-empty string")
    if not isinstance(count, int) or count < 1:
        raise ValueError("target_number.count must be an int >= 1")
    if count > config.max_target_count:
        raise ValueError(f"target_number.count exceeds server limit ({config.max_target_count})")
    return (table, count), None


def register_run_tool(mcp: FastMCP, timeout_seconds: int) -> None:
    """Register ``run_recipe``.

    ``timeout_seconds`` is the Phase-4 pre-lifespan carve-out (see
    ``server.create_app()``): ``@mcp.tool(timeout=...)`` is resolved at
    decoration time, before any lifespan/request context exists, so it can't
    be sourced from ``ctx.lifespan_context`` the way ``paths``/``config`` are
    below. Phase 5 passes it straight to ``@mcp.tool(timeout=timeout_seconds)``,
    replacing the old SIGALRM-based ``time_limit()`` call that used to wrap
    ``generate_data()`` below.

    Honest caveat (see FASTMCP3_REFACTOR_PLAN.md Phase 5's risk note,
    confirmed against the installed fastmcp 3.4.2): ``run_recipe`` is a plain
    ``def`` function, so FastMCP dispatches it to a worker thread via
    ``anyio.to_thread.run_sync(..., abandon_on_cancel=False)`` (fastmcp's
    ``call_sync_fn_in_threadpool``, no override exposed). With
    ``abandon_on_cancel=False`` (anyio's default), a cancellation delivered
    to the *awaiting* task while the worker thread is still running is
    suppressed until the thread finishes on its own — verified directly: a
    ``@mcp.tool(timeout=0.2)`` sync function doing ``time.sleep(2)`` still
    returns a normal, successful result after the full 2s, with no timeout
    error at all. So for this tool, ``timeout=`` does not bound wall-clock
    time the way SIGALRM was originally intended to (and, per the existing
    ``time_limit()`` regression test this phase removes, SIGALRM was *also*
    already a no-op here under fastmcp 3.x's threadpool dispatch — this is a
    lateral move, not a regression from working protection).
    """

    @mcp.tool(
        tags={"execution", "generation"},
        output_schema=tool_output_schema(RunResult),
        annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False),
        timeout=timeout_seconds,
        version="1",
    )
    def run_recipe(
        recipe_path: str | None = None,
        recipe_text: str | None = None,
        options: dict[str, Any] | None = None,
        plugin_options: dict[str, Any] | None = None,
        reps: int | None = None,
        target_number: TargetNumber | None = None,
        output_format: str = "txt",
        capture_output: CaptureMode = "preview",
        strict_mode: bool = True,
        validate_only: bool = False,
        generate_continuation: bool = False,
        *,
        ctx: Context,
    ) -> RunResult | ToolResult:
        """Run a Snowfakery recipe and generate fake data.

        Executes the recipe and returns generated output along with artifact URIs.
        The complete output is always written to disk and available via the
        returned resource URI regardless of ``capture_output`` - that setting
        only controls how much of it also comes back inline in this response.

        Args:
            recipe_path: Path to recipe file (relative to workspace)
            recipe_text: Recipe YAML content as string
            options: User options (--option key=value equivalent)
            plugin_options: Plugin configuration options
            reps: Number of times to repeat the recipe
            target_number: Generate until table reaches count {"table": "X", "count": N}
            output_format: Output format (txt, json, csv, sql, dot, svg, etc.)
            capture_output: How much generated output to include inline, in
                addition to the resource: "preview" (default) is a small
                preview plus output_bytes/record_count so you know how much
                data exists without paying to see all of it; "full" is the
                complete output inline, up to the server's max-capture-chars
                limit; "none" omits inline text entirely.
            strict_mode: Fail on undefined field references
            validate_only: Only validate, don't generate
            generate_continuation: Create continuation file for resuming
        """

        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        config: Config = ctx.lifespan_context["config"]

        text = recipe_text_from_input(
            recipe_path=recipe_path,
            recipe_text=recipe_text,
            workspace_root=paths.root,
        )

        run_id, run_dir = paths.new_run_dir()

        fmt = output_format.lower()
        if fmt not in set(file_extensions):
            raise ValueError(f"Unsupported output_format: {output_format}")

        target_tuple, _ = _safe_stopping_criteria(
            config=config, reps=reps, target_number=target_number
        )

        out_buf: StringIO | None = None
        if capture_output != "none" and fmt in {"txt", "json", "sql", "dot", "svg", "svgz"}:
            out_buf = StringIO()

        artifact_name = f"output.{fmt}"
        artifact_path = run_dir / artifact_name

        output_files: list[Any] = []
        if out_buf is not None:
            output_files.append(out_buf)
        output_files.append(str(artifact_path))

        output_folder: str | None = None
        if fmt == "csv":
            csv_dir = run_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)
            output_folder = str(csv_dir)
            output_files = []

        continuation_path: str | None = None
        if generate_continuation:
            continuation_path = str(run_dir / "continuation.yml")

        try:
            kwargs: dict[str, Any] = {
                "parent_application": MCPApplication(),
                "user_options": dict(options or {}),
                "plugin_options": dict(plugin_options or {}),
                "output_format": fmt,
                "strict_mode": strict_mode,
                "validate_only": validate_only,
            }
            if target_tuple is not None:
                kwargs["target_number"] = target_tuple
            if output_files:
                kwargs["output_files"] = output_files
            if output_folder is not None:
                kwargs["output_folder"] = output_folder
            if continuation_path is not None:
                kwargs["generate_continuation_file"] = continuation_path

            summary = generate_data(StringIO(text), **kwargs)
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

        output_bytes = artifact_path.stat().st_size if artifact_path.exists() else 0

        stdout_text = ""
        stdout_truncated = False
        record_count: int | None = None
        if capture_output != "none" and out_buf is not None:
            # Some output formats (image/diagram renders piped through
            # graphviz) close their file-like output target once rendering
            # finishes, so out_buf.getvalue() would raise ValueError("I/O
            # operation on closed file") - fall back to reading the artifact
            # straight off disk for those instead of crashing (the file
            # write itself always succeeds independent of this).
            full_captured = "" if out_buf.closed else out_buf.getvalue()
            if not full_captured and artifact_path.exists():
                full_captured = read_text_utf8(artifact_path)
            budget = config.max_capture_chars if capture_output == "full" else config.preview_chars
            stdout_text, stdout_truncated, record_count = smart_truncate_output(
                full_captured, output_format=fmt, max_chars=budget
            )

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
            "stdout_text": stdout_text,
            "stdout_truncated": stdout_truncated,
            "output_bytes": output_bytes,
            "record_count": record_count,
            "resources": resources,
            "summary": str(summary),
        }
