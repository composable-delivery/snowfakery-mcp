"""Integration tests for the MCP server over stdio."""

from __future__ import annotations

import json
import textwrap
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _resource_text(result: Any) -> str:
    contents = getattr(result, "contents", None)
    assert isinstance(contents, list) and contents, "Expected non-empty resource contents"
    first = contents[0]
    text = getattr(first, "text", None)
    assert isinstance(text, str), "Expected text resource contents"
    return text


def _tool_payload_text(result: Any) -> str:
    content = getattr(result, "content", None)
    assert isinstance(content, list) and content, "Expected non-empty tool result"
    text = getattr(content[0], "text", None)
    assert isinstance(text, str), "Expected text tool result"
    return text


@pytest.fixture
async def mcp_session() -> AsyncIterator[ClientSession]:
    repo_root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd=str(repo_root),
        env={
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": str(repo_root),
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
    res = await mcp_session.read_resource(cast(Any, "snowfakery://schema/recipe-jsonschema"))
    schema = json.loads(_resource_text(res))
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

    payload = json.loads(_tool_payload_text(out))
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

    payload = json.loads(_tool_payload_text(out))
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

    payload = json.loads(_tool_payload_text(out))
    assert payload["ok"] is True, payload
    assert payload["resources"]
    assert payload["resources"][0].startswith("snowfakery://runs/")


@pytest.mark.anyio
async def test_bundled_docs_and_examples_without_submodule(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    params = StdioServerParameters(
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd=str(repo_root),
        env={
            # Point the server workspace root at an empty temp dir so there is
            # no Snowfakery submodule available under it.
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": str(tmp_path),
            "SNOWFAKERY_MCP_MAX_REPS": "5",
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": "50",
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": "5000",
        },
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            docs = await session.read_resource(cast(Any, "snowfakery://docs/index"))
            docs_text = _resource_text(docs)
            assert "Snowfakery" in docs_text

            examples = await session.read_resource(cast(Any, "snowfakery://examples/list"))
            payload = json.loads(_resource_text(examples))
            assert "examples" in payload
            assert "company.yml" in payload["examples"]

            example = await session.read_resource(cast(Any, "snowfakery://examples/company.yml"))
            example_text = _resource_text(example)
            assert "- object:" in example_text
