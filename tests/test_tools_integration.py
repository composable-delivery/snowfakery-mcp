"""Integration tests for tools using FastMCP in-memory client."""

from __future__ import annotations

import base64
import dataclasses
import json
import shutil
import textwrap
from typing import Any

import pytest
from fastmcp import Client


def get_tool_data(result: Any) -> dict[str, Any]:
    """Extract data from a FastMCP tool result."""
    # FastMCP CallToolResult has .data for structured responses
    if hasattr(result, "data") and result.data is not None:
        data = result.data
        # Typed (non-Union) TypedDict return annotations (Phase 6) make
        # FastMCP's Client parse structured_content into a dynamically
        # generated dataclass (fastmcp.utilities.json_schema_type.Root, or a
        # schema-titled subclass of it) instead of a plain dict - and
        # dataclasses.asdict() recurses through nested dataclass fields
        # (e.g. list_capabilities' "limits"/"resources"), unlike a shallow
        # vars()/__dict__ walk.
        if dataclasses.is_dataclass(data) and not isinstance(data, type):
            return dataclasses.asdict(data)
        # Handle pydantic models
        if hasattr(data, "model_dump"):
            return data.model_dump()
        if isinstance(data, dict):
            return data
        # FastMCP creates dynamic Root objects - convert via __dict__
        if hasattr(data, "__dict__"):
            # Filter out private attributes
            return {k: v for k, v in vars(data).items() if not k.startswith("_")}
        return {"result": data}
    # Fallback to structured_content
    if hasattr(result, "structured_content") and result.structured_content:
        return result.structured_content
    # Last resort: parse from text content
    if hasattr(result, "content") and result.content:
        import json

        text = (
            result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        )
        return json.loads(text)
    raise ValueError(f"Cannot extract data from result: {result}")


@pytest.mark.anyio
async def test_validate_recipe_with_invalid_yaml(mcp_client: Client) -> None:
    """Test validate_recipe with invalid YAML syntax."""
    recipe = "invalid: [yaml: syntax:"

    result = await mcp_client.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": False},
        raise_on_error=False,
    )

    # A malformed recipe is a ToolResult(is_error=True) per Phase 3's error contract.
    assert result.is_error is True
    payload = get_tool_data(result)
    assert payload["valid"] is False
    assert "errors" in payload


@pytest.mark.anyio
async def test_validate_recipe_with_no_snowfakery_version(mcp_client: Client) -> None:
    """Test validate_recipe with recipe missing required fields."""
    recipe = textwrap.dedent(
        """
        - object: Person
          count: 1
        """
    ).strip()

    result = await mcp_client.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": False},
    )

    payload = get_tool_data(result)
    # Without strict mode, missing version might be acceptable
    assert "valid" in payload


@pytest.mark.anyio
async def test_validate_recipe_strict_mode(mcp_client: Client) -> None:
    """Test validate_recipe with strict mode enabled."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Account
          fields:
            Name: ACME
        """
    ).strip()

    result = await mcp_client.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": True},
    )

    payload = get_tool_data(result)
    assert payload["valid"] is True


@pytest.mark.anyio
async def test_analyze_recipe_valid(mcp_client: Client) -> None:
    """Test analyze_recipe with valid recipe."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 5
          fields:
            name: ${{fake.first_name}}
            email: ${{fake.email}}
        """
    ).strip()

    result = await mcp_client.call_tool(
        "analyze_recipe",
        {"recipe_text": recipe},
    )

    payload = get_tool_data(result)
    assert "tables" in payload or "objects" in payload


@pytest.mark.anyio
async def test_analyze_recipe_with_malformed_yaml(mcp_client: Client) -> None:
    """A malformed recipe must return a structured ToolResult(is_error=True),
    not an uncaught exception crossing the transport (Phase 3)."""
    recipe = "invalid: [recipe:"

    result = await mcp_client.call_tool(
        "analyze_recipe",
        {"recipe_text": recipe},
        raise_on_error=False,
    )

    assert result.is_error is True
    payload = get_tool_data(result)
    assert "error" in payload
    assert payload["error"]["kind"]
    assert payload["error"]["message"]


@pytest.mark.anyio
async def test_run_recipe_with_json_output(mcp_client: Client) -> None:
    """Test run_recipe with JSON output format."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 2
          fields:
            name: TestUser
        """
    ).strip()

    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "json",
            "capture_output": "full",
            "strict_mode": True,
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["run_id"]

    # Text artifacts (.json here) must still round-trip through the plain-text
    # read_text_utf8 path, unaffected by the binary-format branch added alongside it.
    artifact_uri = payload["resources"][0]
    content = await mcp_client.read_resource(artifact_uri)
    assert content[0].text.strip().startswith("[")


@pytest.mark.anyio
async def test_run_recipe_output_schema_has_no_synthetic_wrap_envelope(
    mcp_client: Client,
) -> None:
    """run_recipe's return type is Union[RunOkResult, RunErrorResult], which
    FastMCP would otherwise auto-wrap in a synthetic {"result": {...}} envelope
    (top-level anyOf isn't itself an "object" schema). Phase 3's explicit
    output_schema= must avoid that wrap, and the raw structured_content on the
    wire must expose "ok"/"run_id" directly, not nested under "result"."""
    tools = await mcp_client.list_tools()
    run_recipe_tool = next(t for t in tools if t.name == "run_recipe")
    assert run_recipe_tool.outputSchema is not None
    assert not run_recipe_tool.outputSchema.get("x-fastmcp-wrap-result")

    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 1
          fields:
            name: TestUser
        """
    ).strip()

    result = await mcp_client.call_tool(
        "run_recipe",
        {"recipe_text": recipe, "reps": 1, "output_format": "txt"},
    )

    # Raw wire-level structured_content, not the client's unwrapped `.data`.
    assert result.structured_content is not None
    assert "result" not in result.structured_content
    assert result.structured_content["ok"] is True
    assert result.structured_content["run_id"]


@pytest.mark.anyio
@pytest.mark.skipif(shutil.which("dot") is None, reason="requires the graphviz `dot` executable")
async def test_run_recipe_png_artifact_round_trip(mcp_client: Client) -> None:
    """Binary run artifacts (e.g. PNG ERD diagrams) must round-trip as real bytes
    when read back as a resource, not crash with a forced-UTF-8 UnicodeDecodeError."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 2
          fields:
            name: TestUser
        """
    ).strip()

    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "png",
            "capture_output": "none",
            "strict_mode": True,
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert len(payload["resources"]) == 1
    artifact_uri = payload["resources"][0]
    assert artifact_uri.endswith("/output.png")

    content = await mcp_client.read_resource(artifact_uri)
    assert len(content) == 1
    blob_item = content[0]
    assert blob_item.mimeType == "image/png"
    raw_bytes = base64.b64decode(blob_item.blob)
    assert raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.anyio
async def test_run_recipe_with_invalid_recipe(mcp_client: Client) -> None:
    """Test run_recipe with invalid recipe."""
    recipe = "invalid: [recipe:"

    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "txt",
            "capture_output": "full",
            "strict_mode": False,
        },
        raise_on_error=False,
    )

    # A recipe that fails to generate is a ToolResult(is_error=True) per
    # Phase 3's error contract; CallToolResult.isError is now meaningful.
    assert result.is_error is True
    payload = get_tool_data(result)
    # Should indicate failure
    assert payload.get("ok") is False or "error" in payload


@pytest.mark.anyio
async def test_list_capabilities(mcp_client: Client) -> None:
    """Test list_capabilities tool.

    Phase 6 fixed the duplicated "limits" block (the same four scalars used
    to appear both at the top level and nested under "limits"); the nested
    "limits" object is now the single source of truth for these fields.
    """
    result = await mcp_client.call_tool("list_capabilities", {})

    payload = get_tool_data(result)
    assert "max_reps" not in payload
    assert "max_target_count" not in payload
    assert "max_capture_chars" not in payload
    limits = payload["limits"]
    assert "max_reps" in limits
    assert "max_target_count" in limits
    assert "max_capture_chars" in limits
    assert "timeout_seconds" in limits


@pytest.mark.anyio
async def test_list_examples(mcp_client: Client) -> None:
    """Test list_examples tool."""
    result = await mcp_client.call_tool("list_examples", {})

    payload = get_tool_data(result)
    assert "examples" in payload
    assert isinstance(payload["examples"], list)


@pytest.mark.anyio
async def test_list_examples_with_prefix(mcp_client: Client) -> None:
    """Test list_examples tool with prefix filter."""
    result = await mcp_client.call_tool("list_examples", {"prefix": "comp"})

    payload = get_tool_data(result)
    assert "examples" in payload
    # All examples should start with the prefix
    for example in payload["examples"]:
        assert example.startswith("comp") or len(payload["examples"]) == 0


@pytest.mark.anyio
async def test_get_example(mcp_client: Client) -> None:
    """Test get_example tool."""
    result = await mcp_client.call_tool("get_example", {"name": "company.yml"})

    payload = get_tool_data(result)
    assert "content" in payload or "error" in payload


_MANY_RECORDS_RECIPE = textwrap.dedent(
    """
    - snowfakery_version: 3
    - object: Person
      count: 200
      fields:
        name: TestUser
    """
).strip()


@pytest.mark.anyio
async def test_run_recipe_default_capture_output_is_a_small_preview_with_counts(
    mcp_client: Client,
) -> None:
    """Default capture_output ("preview") must not dump the full (potentially
    large) captured output inline - the complete data is always available via
    the resource regardless. It should instead return a small, valid preview
    plus output_bytes/record_count so a caller can tell how much data exists
    without paying the token cost of seeing all of it."""
    result = await mcp_client.call_tool(
        "run_recipe",
        {"recipe_text": _MANY_RECORDS_RECIPE, "output_format": "json"},
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["record_count"] == 200
    assert payload["output_bytes"] > 0
    assert payload["stdout_truncated"] is True
    parsed_preview = json.loads(payload["stdout_text"])  # must still be valid JSON
    assert 0 < len(parsed_preview) < 200

    # The complete, untruncated data is still available via the resource.
    artifact_uri = payload["resources"][0]
    content = await mcp_client.read_resource(artifact_uri)
    assert len(json.loads(content[0].text)) == 200


@pytest.mark.anyio
async def test_run_recipe_capture_output_full_returns_everything_up_to_the_larger_limit(
    mcp_client: Client,
) -> None:
    """capture_output="full" is the explicit opt-in for the old "give me
    everything inline" behavior, bounded by the server's (much larger)
    max_capture_chars limit instead of the small default preview budget."""
    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": _MANY_RECORDS_RECIPE,
            "output_format": "json",
            "capture_output": "full",
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["record_count"] == 200
    assert payload["stdout_truncated"] is False
    assert len(json.loads(payload["stdout_text"])) == 200


@pytest.mark.anyio
async def test_run_recipe_capture_output_none_omits_inline_text(mcp_client: Client) -> None:
    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": _MANY_RECORDS_RECIPE,
            "output_format": "json",
            "capture_output": "none",
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["stdout_text"] == ""
    assert payload["stdout_truncated"] is False
    assert payload["output_bytes"] > 0  # the file was still written, just not inlined
    assert len(payload["resources"]) == 1


@pytest.mark.anyio
@pytest.mark.skipif(shutil.which("dot") is None, reason="requires the graphviz `dot` executable")
async def test_run_recipe_svg_default_capture_output_does_not_crash(mcp_client: Client) -> None:
    """Regression test: Snowfakery's generate_data() closes its output
    file-like target after rendering image/diagram formats (svg/png/dot/
    svgz), so calling .getvalue() on it afterward used to raise
    ValueError("I/O operation on closed file") for every non-"none"
    capture_output value on these formats - pre-existing on main, independent
    of the fastmcp 3.x migration. run_recipe must fall back to reading the
    artifact off disk instead of crashing."""
    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": textwrap.dedent(
                """
                - snowfakery_version: 3
                - object: Person
                  count: 2
                  fields:
                    name: TestUser
                """
            ).strip(),
            "output_format": "svg",
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["stdout_text"].strip().startswith("<?xml")
    assert payload["output_bytes"] > 0
