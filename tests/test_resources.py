"""Tests for MCP resources using FastMCP in-memory client."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp import Client

if TYPE_CHECKING:
    pass


@pytest.mark.anyio
async def test_list_resources(mcp_client: Client[Any]) -> None:
    """Test that resources/list returns all available resources."""
    result = await mcp_client.list_resources()
    resource_uris = {str(r.uri) for r in result}

    # Discovery resources
    assert "snowfakery://providers/list" in resource_uris
    assert "snowfakery://plugins/list" in resource_uris
    assert "snowfakery://formats/info" in resource_uris

    # Static resources
    assert "snowfakery://schema/recipe-jsonschema" in resource_uris
    assert "snowfakery://docs/index" in resource_uris
    assert "snowfakery://examples/list" in resource_uris


@pytest.mark.anyio
async def test_providers_list_resource(mcp_client: Client[Any]) -> None:
    """Test reading the providers/list resource."""
    content = await mcp_client.read_resource("snowfakery://providers/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    assert "categories" in data
    assert isinstance(data["categories"], dict)
    # Should have several provider categories (person, company, etc.)
    assert len(data["categories"]) > 0


@pytest.mark.anyio
async def test_plugins_list_resource(mcp_client: Client[Any]) -> None:
    """Test reading the plugins/list resource."""
    content = await mcp_client.read_resource("snowfakery://plugins/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    assert "plugins" in data
    assert isinstance(data["plugins"], dict)
    plugin_names = set(data["plugins"].keys())

    # Should include known built-in plugins
    expected_plugins = {"Math", "Counters", "UniqueId"}
    assert expected_plugins.issubset(plugin_names)


@pytest.mark.anyio
async def test_plugins_list_has_methods(mcp_client: Client[Any]) -> None:
    """Test that plugins in the list have method information."""
    content = await mcp_client.read_resource("snowfakery://plugins/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    # Each plugin should have methods
    for _plugin_name, plugin_info in data["plugins"].items():
        assert "methods" in plugin_info
        assert isinstance(plugin_info["methods"], list)


@pytest.mark.anyio
async def test_formats_info_resource(mcp_client: Client[Any]) -> None:
    """Test reading the formats/info resource."""
    content = await mcp_client.read_resource("snowfakery://formats/info")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    assert "formats" in data
    assert isinstance(data["formats"], dict)
    format_names = set(data["formats"].keys())

    # Should include common output formats
    expected_formats = {"txt", "json", "csv"}
    assert expected_formats.issubset(format_names)


@pytest.mark.anyio
async def test_formats_info_has_details(mcp_client: Client[Any]) -> None:
    """Test that formats in the info have detailed information."""
    content = await mcp_client.read_resource("snowfakery://formats/info")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    for _format_name, format_info in data["formats"].items():
        assert "name" in format_info
        # Check if it has at least description
        assert "description" in format_info


@pytest.mark.anyio
async def test_docs_index_resource(mcp_client: Client[Any]) -> None:
    """Test reading the docs/index resource."""
    content = await mcp_client.read_resource("snowfakery://docs/index")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])

    assert "Snowfakery" in text or "snowfakery" in text.lower()
    assert len(text) > 100  # Should have substantial documentation


@pytest.mark.anyio
async def test_examples_list_resource(mcp_client: Client[Any]) -> None:
    """Test reading the examples/list resource."""
    content = await mcp_client.read_resource("snowfakery://examples/list")
    text = content[0].text if hasattr(content[0], "text") else str(content[0])
    data = json.loads(text)

    assert "examples" in data
    assert isinstance(data["examples"], list)
    # Should have at least company.yml
    assert len(data["examples"]) > 0


@pytest.mark.anyio
async def test_example_resource_readable(mcp_client: Client[Any]) -> None:
    """Test reading individual example resources."""
    # First get the list
    list_content = await mcp_client.read_resource("snowfakery://examples/list")
    list_text = list_content[0].text if hasattr(list_content[0], "text") else str(list_content[0])
    list_data = json.loads(list_text)

    if list_data["examples"]:
        example_name = list_data["examples"][0]
        content = await mcp_client.read_resource(f"snowfakery://examples/{example_name}")
        text = content[0].text if hasattr(content[0], "text") else str(content[0])

        # Example should contain recipe content
        assert len(text) > 0
        assert "object:" in text or "Object:" in text  # YAML recipe syntax
