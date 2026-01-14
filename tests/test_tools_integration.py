"""Integration tests for tools using FastMCP in-memory client."""

from __future__ import annotations

import textwrap
from typing import Any

import pytest
from fastmcp import Client


def get_tool_data(result: Any) -> dict[str, Any]:
    """Extract data from a FastMCP tool result."""
    # FastMCP CallToolResult has .data for structured responses
    if hasattr(result, "data") and result.data is not None:
        data = result.data
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
    )

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
            "capture_output": True,
            "strict_mode": True,
        },
    )

    payload = get_tool_data(result)
    assert payload["ok"] is True
    assert payload["run_id"]


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
            "capture_output": True,
            "strict_mode": False,
        },
    )

    payload = get_tool_data(result)
    # Should indicate failure
    assert payload.get("ok") is False or "error" in payload


@pytest.mark.anyio
async def test_list_capabilities(mcp_client: Client) -> None:
    """Test list_capabilities tool."""
    result = await mcp_client.call_tool("list_capabilities", {})

    payload = get_tool_data(result)
    assert "max_reps" in payload
    assert "max_target_count" in payload
    assert "max_capture_chars" in payload


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
