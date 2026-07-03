"""Unit-level branch coverage for resources/static.py, driven through a real
FastMCP server instance and a real fastmcp.Client (in-memory transport) instead
of a MagicMock(spec=FastMCP) decorator-capture harness.

Calling the real, decorator-registered functions via Client exercises FastMCP's
actual URI-template matching and exception-to-error conversion - the exact
safety net that let past bugs (e.g. the ctx.read_resource() interpolation bug)
ship undetected behind a mocked registration layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP
from mcp.shared.exceptions import McpError

from conftest import lifespan_stub
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.resources.static import register_static_resources


def _resource_text(content: list[Any]) -> str:
    first = content[0]
    return str(first.text) if hasattr(first, "text") else str(first)


@pytest.mark.anyio
async def test_recipe_schema_dev_mode(tmp_path: Path) -> None:
    """Schema is read from the local Snowfakery submodule when present (dev mode)."""
    schema_dir = tmp_path / "Snowfakery" / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "snowfakery_recipe.jsonschema.json").write_text('{"local": true}')

    paths = WorkspacePaths(root=tmp_path)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_static_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://schema/recipe-jsonschema")

    assert _resource_text(content) == '{"local": true}'
    assert content[0].mimeType == "application/json"


@pytest.mark.anyio
async def test_recipe_schema_bundled_fallback(tmp_path: Path) -> None:
    """Schema falls back to the bundled package copy when no submodule is present."""
    paths = WorkspacePaths(root=tmp_path)  # No "Snowfakery" dir here.
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_static_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://schema/recipe-jsonschema")

    text = _resource_text(content)
    # Real bundled JSON Schema file - confirms we hit the fallback branch, not a mock.
    assert '"$schema"' in text
    assert content[0].mimeType == "application/json"


@pytest.mark.anyio
async def test_example_resource_traversable_bundled(tmp_path: Path) -> None:
    """example_resource reads from the bundled Traversable when no submodule examples exist."""
    paths = WorkspacePaths(root=tmp_path)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_static_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://examples/test_alpha.yml")

    assert len(_resource_text(content)) > 0


@pytest.mark.anyio
async def test_example_resource_path_outside_workspace(tmp_path: Path) -> None:
    """example_resource serves content when examples_root() resolves to a real
    filesystem Path that lives outside the configured workspace root."""
    external_root = tmp_path / "external"
    external_root.mkdir()
    (external_root / "test.yml").write_text("EXTERNAL_CONTENT")

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    paths = WorkspacePaths(root=workspace_root)

    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_static_resources(mcp)

    with patch("snowfakery_mcp.resources.static.examples_root", return_value=external_root):
        async with Client(mcp) as client:
            content = await client.read_resource("snowfakery://examples/test.yml")

    assert _resource_text(content) == "EXTERNAL_CONTENT"


@pytest.mark.anyio
async def test_example_resource_missing_raises_mcp_error(tmp_path: Path) -> None:
    """Missing examples surface as a real MCP resource error via the Client, not a
    bypassed raw-function exception."""
    paths = WorkspacePaths(root=tmp_path)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_static_resources(mcp)

    async with Client(mcp) as client:
        with pytest.raises(McpError, match="not found"):
            await client.read_resource("snowfakery://examples/does-not-exist.yml")
