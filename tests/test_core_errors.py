"""Tests for the shared exception -> ToolError translation helper.

``tool_error_from_exception`` replaces the identical ``DataGenError``/
``(OSError, RuntimeError, ValueError)`` except-block trio that used to be
copy-pasted in ``tools/run.py``, ``tools/mapping.py``, and ``core/validate.py``
(see FASTMCP3_REFACTOR_PLAN.md Phase 3), and, as of Phase 5, also translates
``McpError`` (FastMCP's ``@mcp.tool(timeout=...)`` deadline signal).
"""

from __future__ import annotations

from mcp.shared.exceptions import McpError
from mcp.types import ErrorData
from snowfakery.data_gen_exceptions import DataGenError

from snowfakery_mcp.core.errors import tool_error_from_exception


def test_data_gen_error_uses_structured_fields() -> None:
    """DataGenError carries real filename/line info that should be preserved."""
    exc = DataGenError("bad recipe", filename="recipe.yml", line_num=42)

    err = tool_error_from_exception(exc)

    assert err == {
        "kind": "DataGenError",
        "message": "bad recipe",
        "filename": "recipe.yml",
        "line": 42,
    }


def test_data_gen_error_subclass_reports_its_own_kind() -> None:
    """The 'kind' field reflects the concrete exception class, not the base."""

    class CustomDataGenError(DataGenError):
        pass

    exc = CustomDataGenError("nope", filename=None, line_num=None)

    err = tool_error_from_exception(exc)

    assert err["kind"] == "CustomDataGenError"
    assert err["filename"] is None
    assert err["line"] is None


def test_mcp_error_timeout_is_classified_as_timeout_kind() -> None:
    """A ``timeout=`` deadline's McpError (see fastmcp.tools.function_tool)
    is classified as ``kind="TimeoutError"`` from its message text, since
    McpError carries no dedicated timeout subtype of its own."""
    exc = McpError(
        ErrorData(code=-32000, message="Tool 'run_recipe' execution timed out after 30.0s")
    )

    err = tool_error_from_exception(exc)

    assert err == {
        "kind": "TimeoutError",
        "message": "Tool 'run_recipe' execution timed out after 30.0s",
        "filename": None,
        "line": None,
    }


def test_mcp_error_non_timeout_falls_back_to_generic_mcp_kind() -> None:
    """A non-timeout McpError (e.g. some other protocol-level failure) still
    gets the shared shape, just without the "TimeoutError" kind."""
    exc = McpError(ErrorData(code=-32603, message="Internal error: boom"))

    err = tool_error_from_exception(exc)

    assert err == {
        "kind": "MCPError",
        "message": "Internal error: boom",
        "filename": None,
        "line": None,
    }


def test_generic_exceptions_fall_back_to_message_only() -> None:
    """OSError/RuntimeError/ValueError all use the generic str(exc) shape."""
    for exc in (
        OSError("disk full"),
        RuntimeError("boom"),
        ValueError("bad value"),
    ):
        err = tool_error_from_exception(exc)
        assert err["kind"] == type(exc).__name__
        assert err["message"] == str(exc)
        assert err["filename"] is None
        assert err["line"] is None
