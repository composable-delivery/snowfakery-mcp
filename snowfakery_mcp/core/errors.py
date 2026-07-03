"""Shared exception-to-``ToolError`` translation for the execution tools.

``run_recipe``, ``generate_mapping``, and ``validate_recipe_logic`` all catch the
same trio of exception types raised by Snowfakery during recipe generation —
``DataGenError`` (a bad recipe) and the catch-all
``(OSError, RuntimeError, ValueError)`` for anything else unexpected — and turn
whichever one fired into the same :class:`~snowfakery_mcp.core.types.ToolError`
shape. This module centralizes that translation so it isn't hand-copied in
three places.

As of Phase 5 (see ``FASTMCP3_REFACTOR_PLAN.md``), this also translates
``McpError`` — the shape FastMCP's ``@mcp.tool(timeout=...)`` raises when a
tool's configured deadline expires (``fastmcp.tools.function_tool``, wrapping
``anyio.fail_after``'s ``TimeoutError`` as ``McpError(ErrorData(code=-32000,
message="Tool '...' execution timed out after ...s"))``). Note that FastMCP
raises this *outside* any tool function's own call frame — the cancellation
unwinds the coroutine/task awaiting the tool, not code running inside
``run_recipe``/``generate_mapping``/``validate_recipe_logic``'s own
``try``/``except`` blocks (confirmed directly against the installed fastmcp
3.4.2; see those functions' docstrings for the full explanation) — so this
branch is not reachable from those specific ``except`` blocks in production.
It is provided so any code that *does* observe an ``McpError`` directly (unit
tests; a future middleware hook) gets the same structured shape as every
other failure mode here instead of hand-rolling one.
"""

from __future__ import annotations

from mcp.shared.exceptions import McpError
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.types import ToolError


def tool_error_from_exception(exc: Exception) -> ToolError:
    """Translate a caught exception into the shared :class:`ToolError` shape.

    ``DataGenError`` carries structured ``.message``/``.filename``/``.line_num``
    fields pointing at the offending recipe location. ``McpError`` (see module
    docstring) carries a ``.error.message``; it's classified as
    ``kind="TimeoutError"`` when that message indicates a ``timeout=``
    deadline, else the generic ``kind="MCPError"``. Every other exception this
    is called with (``OSError``, ``RuntimeError``, ``ValueError``, ...) only
    has a message, so ``filename``/``line`` are ``None``.
    """

    if isinstance(exc, DataGenError):
        return {
            "kind": type(exc).__name__,
            "message": exc.message,
            "filename": exc.filename,
            "line": exc.line_num,
        }

    if isinstance(exc, McpError):
        message = exc.error.message
        kind = "TimeoutError" if "timed out" in message.lower() else "MCPError"
        return {
            "kind": kind,
            "message": message,
            "filename": None,
            "line": None,
        }

    return {
        "kind": type(exc).__name__,
        "message": str(exc),
        "filename": None,
        "line": None,
    }
