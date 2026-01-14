"""Tests for MCP resources."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from mcp.client.session import ClientSession
from tests.conftest import _resource_text


@pytest.mark.anyio
async def test_list_resources(mcp_session: ClientSession) -> None:
    """Test that resources/list returns all available resources."""
    result = await mcp_session.list_resources()
    resource_uris = {r.uri for r in result.resources}

    # Discovery resources
    assert "snowfakery://providers/list" in resource_uris
    assert "snowfakery://plugins/list" in resource_uris
    assert "snowfakery://formats/info" in resource_uris

    # Static resources
    assert "snowfakery://schema/recipe-jsonschema" in resource_uris
    assert "snowfakery://docs/index" in resource_uris
    assert "snowfakery://examples/list" in resource_uris


@pytest.mark.anyio
async def test_providers_list_resource(mcp_session: ClientSession) -> None:
    """Test reading the providers/list resource."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://providers/list"))
    text = _resource_text(res)
    data = json.loads(text)

    assert "providers" in data
    assert isinstance(data["providers"], dict)
    # Should have several provider categories (basic, company, credit_card, etc.)
    assert len(data["providers"]) > 0


@pytest.mark.anyio
async def test_plugins_list_resource(mcp_session: ClientSession) -> None:
    """Test reading the plugins/list resource."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://plugins/list"))
    text = _resource_text(res)
    data = json.loads(text)

    assert "plugins" in data
    assert isinstance(data["plugins"], list)
    plugin_names = {p["name"] for p in data["plugins"]}

    # Should include known built-in plugins
    expected_plugins = {"Math", "Counters", "UniqueId"}
    assert expected_plugins.issubset(plugin_names)


@pytest.mark.anyio
async def test_plugins_list_has_methods(mcp_session: ClientSession) -> None:
    """Test that plugins in the list have method information."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://plugins/list"))
    text = _resource_text(res)
    data = json.loads(text)

    # Each plugin should have methods
    for plugin in data["plugins"]:
        assert "name" in plugin
        assert "methods" in plugin
        assert isinstance(plugin["methods"], list)


@pytest.mark.anyio
async def test_formats_info_resource(mcp_session: ClientSession) -> None:
    """Test reading the formats/info resource."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://formats/info"))
    text = _resource_text(res)
    data = json.loads(text)

    assert "formats" in data
    assert isinstance(data["formats"], list)
    format_names = {f["name"] for f in data["formats"]}

    # Should include common output formats
    expected_formats = {"txt", "json", "csv"}
    assert expected_formats.issubset(format_names)


@pytest.mark.anyio
async def test_formats_info_has_details(mcp_session: ClientSession) -> None:
    """Test that formats in the info have detailed information."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://formats/info"))
    text = _resource_text(res)
    data = json.loads(text)

    for format_info in data["formats"]:
        assert "name" in format_info
        # Check if it has at least description or use_cases
        assert "description" in format_info or "use_cases" in format_info


@pytest.mark.anyio
async def test_docs_index_resource(mcp_session: ClientSession) -> None:
    """Test reading the docs/index resource."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://docs/index"))
    text = _resource_text(res)

    assert "Snowfakery" in text or "snowfakery" in text.lower()
    assert len(text) > 100  # Should have substantial documentation


@pytest.mark.anyio
async def test_examples_list_resource(mcp_session: ClientSession) -> None:
    """Test reading the examples/list resource."""
    res = await mcp_session.read_resource(cast(Any, "snowfakery://examples/list"))
    text = _resource_text(res)
    data = json.loads(text)

    assert "examples" in data
    assert isinstance(data["examples"], list)
    # Should have at least company.yml
    assert len(data["examples"]) > 0


@pytest.mark.anyio
async def test_example_resource_readable(mcp_session: ClientSession) -> None:
    """Test reading individual example resources."""
    # First get the list
    list_res = await mcp_session.read_resource(cast(Any, "snowfakery://examples/list"))
    list_text = _resource_text(list_res)
    list_data = json.loads(list_text)

    if list_data["examples"]:
        example_name = list_data["examples"][0]
        res = await mcp_session.read_resource(cast(Any, f"snowfakery://examples/{example_name}"))
        text = _resource_text(res)

        # Example should contain recipe content
        assert len(text) > 0
        assert "object:" in text or "Object:" in text  # YAML recipe syntax
