from __future__ import annotations

import json
import textwrap
from collections.abc import AsyncIterator

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.fixture
async def mcp_session() -> AsyncIterator[ClientSession]:
    params = StdioServerParameters(
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd="/workspaces/snowfakery-mcp",
        env={
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": "/workspaces/snowfakery-mcp",
            "SNOWFAKERY_MCP_MAX_REPS": "5",
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": "50",
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": "5000",
        },
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


@pytest.mark.anyio
async def test_list_tools_contains_core_tools(mcp_session: ClientSession) -> None:
    result = await mcp_session.list_tools()
    tool_names = {t.name for t in result.tools}

    assert "list_capabilities" in tool_names
    assert "validate_recipe" in tool_names
    assert "analyze_recipe" in tool_names
    assert "run_recipe" in tool_names


@pytest.mark.anyio
async def test_read_schema_resource(mcp_session: ClientSession) -> None:
    res = await mcp_session.read_resource("snowfakery://schema/recipe-jsonschema")
    assert res.contents

    text = res.contents[0].text
    assert text is not None

    schema = json.loads(text)
    assert schema.get("$schema")
    assert schema.get("title")


@pytest.mark.anyio
async def test_validate_recipe_ok(mcp_session: ClientSession) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 2
          fields:
            name: Buster
        """
    ).strip()

    out = await mcp_session.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": True},
    )

    payload_text = out.content[0].text
    assert payload_text is not None
    payload = json.loads(payload_text)
    assert payload["valid"] is True, payload


@pytest.mark.anyio
async def test_run_recipe_txt(mcp_session: ClientSession) -> None:
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 1
          fields:
            name: Buster
        """
    ).strip()

    out = await mcp_session.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "txt",
            "capture_output": True,
            "strict_mode": True,
        },
    )

    payload_text = out.content[0].text
    assert payload_text is not None
    payload = json.loads(payload_text)
    assert payload["ok"] is True, payload
    assert payload["run_id"]
    assert isinstance(payload["resources"], list)


@pytest.mark.anyio
async def test_generate_mapping(mcp_session: ClientSession) -> None:
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

    out = await mcp_session.call_tool("generate_mapping", {"recipe_text": recipe})

    payload_text = out.content[0].text
    assert payload_text is not None
    payload = json.loads(payload_text)
    assert payload["ok"] is True, payload
    assert payload["resources"]
    assert payload["resources"][0].startswith("snowfakery://runs/")
