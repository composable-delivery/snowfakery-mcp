from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import TypeAdapter


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
    output_bytes: int
    record_count: int | None
    resources: list[str]
    summary: str


RunResult = RunOkResult | RunErrorResult


class LimitsResult(TypedDict):
    timeout_seconds: int
    max_capture_chars: int
    preview_chars: int
    max_reps: int
    max_target_count: int


class CapabilitiesResources(TypedDict):
    schema: str
    docs: list[str]
    examples: str


class CapabilitiesResult(TypedDict):
    snowfakery_version: str
    supported_output_formats: list[str]
    limits: LimitsResult
    resources: CapabilitiesResources


class ExampleListResult(TypedDict):
    examples: list[str]


class ExampleResult(TypedDict):
    name: str
    path: str
    content: str


class DocSearchHit(TypedDict):
    doc: str
    line: int
    snippet: str


class DocsSearchResult(TypedDict):
    query: str
    hits: list[DocSearchHit]
    truncated: bool


class AnalyzeTableInfo(TypedDict):
    fields: list[str]
    friends: list[str]
    has_update_keys: bool


class AnalyzeRandomReference(TypedDict):
    function: str | None
    line: int | None
    filename: str | None


class AnalyzeResult(TypedDict):
    version: int
    plugins_declared: list[str]
    options_declared: list[str]
    tables: dict[str, AnalyzeTableInfo]
    uses_random_reference: list[AnalyzeRandomReference]


class MappingOkResult(TypedDict):
    run_id: str
    ok: Literal[True]
    mapping_preview: str
    mapping_truncated: bool
    resources: list[str]


class MappingErrorResult(TypedDict):
    run_id: str
    ok: Literal[False]
    error: ToolError
    resources: list[str]


MappingResult = MappingOkResult | MappingErrorResult


JSONValue = Any


def tool_output_schema(type_: Any) -> dict[str, Any]:
    """Build an explicit ``@mcp.tool(output_schema=...)`` value for ``type_``.

    FastMCP only skips its synthetic ``{"result": {...}}`` wrapping (see
    ``x-fastmcp-wrap-result`` in fastmcp's ``tools/function_parsing.py``) when the
    schema's *top level* is itself a JSON object (``type: object`` or a
    ``properties`` key). A ``Union`` of TypedDicts (e.g. :data:`RunResult`)
    otherwise renders as a top-level ``anyOf``/``oneOf``, which triggers the wrap
    even though every branch of the union is itself an object. Layering an
    explicit ``type: object`` alongside the real ``anyOf`` validation keeps the
    precise per-branch schema while satisfying FastMCP's top-level object check.
    """

    schema = TypeAdapter(type_).json_schema(mode="serialization")
    if schema.get("type") != "object" and "properties" not in schema:
        schema = {"type": "object", **schema}
    return schema
