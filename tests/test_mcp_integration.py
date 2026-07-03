"""Integration tests for the MCP server using FastMCP in-memory client."""

# pylint: disable=missing-function-docstring,redefined-outer-name

from __future__ import annotations

import dataclasses
import json
import textwrap
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp import Client

if TYPE_CHECKING:
    pass


def get_tool_data(result: Any) -> dict[str, Any]:
    """Extract data from a FastMCP tool result."""
    if hasattr(result, "data") and result.data is not None:
        data: Any = result.data
        # Typed (non-Union) TypedDict return annotations (Phase 6) make
        # FastMCP's Client parse structured_content into a dynamically
        # generated dataclass instead of a plain dict; dataclasses.asdict()
        # recurses through nested dataclass fields, unlike a shallow
        # vars()/__dict__ walk.
        if dataclasses.is_dataclass(data) and not isinstance(data, type):
            return dict(dataclasses.asdict(data))
        if hasattr(data, "model_dump"):
            return dict(data.model_dump())
        if isinstance(data, dict):
            return data
        if hasattr(data, "__dict__"):
            return {k: v for k, v in vars(data).items() if not k.startswith("_")}
        return {"result": data}
    if hasattr(result, "structured_content") and result.structured_content:
        structured: Any = result.structured_content
        if isinstance(structured, dict):
            return structured
        return {"result": structured}
    if hasattr(result, "content") and result.content:
        text: str = (
            result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        )
        parsed: Any = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"result": parsed}
    raise ValueError(f"Cannot extract data from result: {result}")


@pytest.mark.anyio
async def test_list_tools_contains_core_tools(mcp_client: Client[Any]) -> None:
    tools = await mcp_client.list_tools()
    tool_names = {t.name for t in tools}

    assert "list_capabilities" in tool_names
    assert "validate_recipe" in tool_names
    assert "analyze_recipe" in tool_names
    assert "run_recipe" in tool_names


@pytest.mark.anyio
async def test_list_tools_annotations_for_representative_sample(
    mcp_client: Client[Any],
) -> None:
    """Phase 6: every tool now declares ``ToolAnnotations`` (see
    FASTMCP3_REFACTOR_PLAN.md Phase 6, step 3) - discovery/analysis tools are
    read-only + idempotent, the two execution tools are neither, and the
    agentic tool is flagged as interacting with an "open world" (the
    client's LLM)."""
    tools = {t.name: t for t in await mcp_client.list_tools()}

    # Every registered tool must declare *some* annotations (the phase's
    # stated goal is "ToolAnnotations for every tool"), not just the ones
    # spot-checked in detail below.
    for tool in tools.values():
        assert tool.annotations is not None, f"{tool.name} has no ToolAnnotations"

    for discovery_tool in (
        "list_capabilities",
        "list_examples",
        "get_example",
        "get_schema",
        "search_docs",
        "analyze_recipe",
        "validate_recipe",
    ):
        annotations = tools[discovery_tool].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is True, discovery_tool
        assert annotations.idempotentHint is True, discovery_tool

    for execution_tool in ("run_recipe", "generate_mapping"):
        annotations = tools[execution_tool].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is False, execution_tool
        assert annotations.idempotentHint is False, execution_tool

    agentic_annotations = tools["iterative_recipe_gen"].annotations
    assert agentic_annotations is not None
    assert agentic_annotations.openWorldHint is True


@pytest.mark.anyio
async def test_list_capabilities_output_schema_is_typed(mcp_client: Client[Any]) -> None:
    """Phase 6: list_capabilities previously advertised the generic
    ``dict[str, Any]`` output schema (``{"type": "object", "additionalProperties":
    true}``, no field-level shape); it now declares a real ``CapabilitiesResult``
    shape via its TypedDict return annotation."""
    tools = {t.name: t for t in await mcp_client.list_tools()}
    schema = tools["list_capabilities"].outputSchema

    assert schema is not None
    assert schema.get("additionalProperties") is not True
    assert set(schema.get("required", [])) == {
        "snowfakery_version",
        "supported_output_formats",
        "limits",
        "resources",
    }
    limits_schema = schema["properties"]["limits"]
    assert set(limits_schema.get("required", [])) == {
        "timeout_seconds",
        "max_capture_chars",
        "preview_chars",
        "max_reps",
        "max_target_count",
    }


@pytest.mark.anyio
async def test_read_schema_resource(mcp_client: Client[Any]) -> None:
    content = await mcp_client.read_resource("snowfakery://schema/recipe-jsonschema")
    # FastMCP returns content as a list of content items
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    schema = json.loads(text)
    assert schema.get("$schema")
    assert schema.get("title")
    assert content[0].mimeType == "application/json"


@pytest.mark.anyio
async def test_validate_recipe_ok(mcp_client: Client[Any]) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 2
          fields:
            name: Buster
        """
    ).strip()

    result = await mcp_client.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": True},
    )

    payload = get_tool_data(result)
    assert payload["valid"] is True, payload


@pytest.mark.anyio
async def test_run_recipe_txt(mcp_client: Client[Any]) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 1
          fields:
            name: Buster
        """
    ).strip()

    result = await mcp_client.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "txt",
            "capture_output": "full",
            "strict_mode": True,
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True, payload
    assert payload["run_id"]
    assert isinstance(payload["resources"], list)


@pytest.mark.anyio
async def test_generate_mapping(mcp_client: Client[Any]) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Account
          fields:
            Name: ACME
        - object: Contact
          fields:
            FirstName: Buster
            AccountId:
              reference: Account
        """
    ).strip()

    result = await mcp_client.call_tool("generate_mapping", {"recipe_text": recipe})

    payload = get_tool_data(result)
    assert payload["ok"] is True, payload
    assert payload["resources"]
    assert payload["resources"][0].startswith("snowfakery://runs/")


@pytest.mark.anyio
async def test_generate_mapping_with_invalid_recipe(mcp_client: Client[Any]) -> None:
    """A recipe that fails to generate is a ToolResult(is_error=True) per
    Phase 3's shared error contract, same as run_recipe/validate_recipe."""
    result = await mcp_client.call_tool(
        "generate_mapping",
        {"recipe_text": "invalid: [recipe:"},
        raise_on_error=False,
    )

    assert result.is_error is True
    payload = get_tool_data(result)
    assert payload["ok"] is False
    assert payload["error"]["kind"]


@pytest.mark.anyio
async def test_list_examples(mcp_client: Client[Any]) -> None:
    result = await mcp_client.call_tool("list_examples", {})
    payload = get_tool_data(result)
    assert "examples" in payload
    assert isinstance(payload["examples"], list)


@pytest.mark.anyio
async def test_get_example(mcp_client: Client[Any]) -> None:
    result = await mcp_client.call_tool("get_example", {"name": "company.yml"})
    payload = get_tool_data(result)
    assert "content" in payload
    assert "- object:" in payload["content"]


@pytest.mark.anyio
async def test_list_capabilities(mcp_client: Client[Any]) -> None:
    result = await mcp_client.call_tool("list_capabilities", {})
    payload = get_tool_data(result)
    assert "snowfakery_version" in payload
    assert "supported_output_formats" in payload
    # Phase 6 fixed list_capabilities' duplicated limits block - these four
    # scalars now live only under "limits", not also at the top level.
    assert "max_reps" not in payload
    assert isinstance(payload["limits"], dict)
    assert isinstance(payload["limits"]["max_reps"], int)
    assert isinstance(payload["limits"]["timeout_seconds"], int)


@pytest.mark.anyio
async def test_analyze_recipe(mcp_client: Client[Any]) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Account
          fields:
            Name: ACME
        """
    ).strip()

    result = await mcp_client.call_tool("analyze_recipe", {"recipe_text": recipe})
    payload = get_tool_data(result)
    assert "tables" in payload
    assert "Account" in payload["tables"]


@pytest.mark.anyio
async def test_search_docs(mcp_client: Client[Any]) -> None:
    result = await mcp_client.call_tool("search_docs", {"query": "fake", "limit": 5})
    payload = get_tool_data(result)
    assert "hits" in payload
    assert isinstance(payload["hits"], list)


@pytest.mark.anyio
async def test_get_schema(mcp_client: Client[Any]) -> None:
    result = await mcp_client.call_tool("get_schema", {})
    payload = get_tool_data(result)
    assert "schema" in payload
    # get_schema() now returns the already-parsed dict directly (json.loads()'d
    # server-side) instead of a double-JSON-encoded string.
    schema = payload["schema"]
    assert isinstance(schema, dict)
    assert "$schema" in schema


@pytest.mark.anyio
async def test_read_discovery_resources(mcp_client: Client[Any]) -> None:
    """Test reading the discovery resources (providers, plugins, formats)."""
    # Providers list
    content = await mcp_client.read_resource("snowfakery://providers/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    providers = json.loads(text)
    assert "categories" in providers

    # Plugins list
    content = await mcp_client.read_resource("snowfakery://plugins/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    plugins = json.loads(text)
    assert "plugins" in plugins

    # Formats info
    content = await mcp_client.read_resource("snowfakery://formats/info")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    formats = json.loads(text)
    assert "formats" in formats


@pytest.mark.anyio
async def test_list_prompts(mcp_client: Client[Any]) -> None:
    prompts = await mcp_client.list_prompts()
    prompt_names = {p.name for p in prompts}
    assert "author_recipe" in prompt_names
    assert "debug_recipe" in prompt_names


@pytest.mark.anyio
async def test_list_resources(mcp_client: Client[Any]) -> None:
    resources = await mcp_client.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert "snowfakery://schema/recipe-jsonschema" in resource_uris
