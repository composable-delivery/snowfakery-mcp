from __future__ import annotations

from typing import Any, Literal, TypedDict


class ErrorLocation(TypedDict, total=False):
    filename: str
    line: int


class ToolError(TypedDict):
    kind: str
    message: str
    filename: str | None
    line: int | None


class ValidateResult(TypedDict):
    valid: bool
    errors: list[ToolError]


class TargetNumber(TypedDict):
    table: str
    count: int


class RunErrorResult(TypedDict):
    run_id: str
    ok: Literal[False]
    error: ToolError
    resources: list[str]


class RunOkResult(TypedDict):
    run_id: str
    ok: Literal[True]
    output_format: str
    stdout_text: str
    stdout_truncated: bool
    resources: list[str]
    summary: str


RunResult = RunOkResult | RunErrorResult


JSONValue = Any
