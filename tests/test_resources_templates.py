"""Unit-level branch coverage for resources/templates.py, driven through a real
FastMCP server instance and a real fastmcp.Client (in-memory transport) instead
of a MagicMock(spec=FastMCP) decorator-capture harness.

Note on path-traversal probing: MCP resource URIs are parsed as real URLs, and
FastMCP/pydantic's AnyUrl normalizes a literal ".." path segment away before it
ever reaches the registered function (e.g. "templates/../x" arrives as
"templates/x"). A percent-encoded segment ("..%2Fx") survives that
normalization and is what actually reaches get_template's `path_str` argument,
so that's what's used below to exercise the real "Access denied" branch end to
end - a literal "../x" URI wouldn't reach that code path via the wire protocol
at all, which the old bypassed-function unit test couldn't have told us.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from mcp.shared.exceptions import McpError

from conftest import lifespan_stub
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.resources.templates import register_template_resources


def _resource_text(content: list) -> str:
    first = content[0]
    return str(first.text) if hasattr(first, "text") else str(first)


@pytest.fixture
def templates_workspace(tmp_path: Path) -> WorkspacePaths:
    root = tmp_path / "workspace"
    templates_root = root / "Snowfakery-Recipe-Templates" / "snowfakery_samples"
    templates_root.mkdir(parents=True)

    (templates_root / "template1.yml").write_text("content1")
    (templates_root / "subdir").mkdir()
    (templates_root / "subdir" / "template2.yml").write_text("content2")

    return WorkspacePaths(root=root)


@pytest.mark.anyio
async def test_list_templates_success(templates_workspace: WorkspacePaths) -> None:
    """Test listing templates when directory exists."""
    mcp = FastMCP("test", lifespan=lifespan_stub(templates_workspace))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://templates/list")

    data = json.loads(_resource_text(content))
    assert "templates" in data
    templates = data["templates"]
    assert "template1.yml" in templates
    assert "subdir/template2.yml" in templates


@pytest.mark.anyio
async def test_list_templates_missing_dir(tmp_path: Path) -> None:
    """Test listing templates when directory is missing."""
    root = tmp_path / "empty_workspace"
    root.mkdir()
    paths = WorkspacePaths(root=root)

    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://templates/list")

    data = json.loads(_resource_text(content))
    assert data["templates"] == []
    assert "note" in data


@pytest.mark.anyio
async def test_get_template_success(templates_workspace: WorkspacePaths) -> None:
    """Test getting a template's content."""
    mcp = FastMCP("test", lifespan=lifespan_stub(templates_workspace))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        content = await client.read_resource("snowfakery://templates/template1.yml")
        assert _resource_text(content) == "content1"

        content = await client.read_resource("snowfakery://templates/subdir/template2.yml")
        assert _resource_text(content) == "content2"


@pytest.mark.anyio
async def test_get_template_security(templates_workspace: WorkspacePaths) -> None:
    """Test path traversal prevention using a percent-encoded ".." segment, the
    payload shape that actually survives URI normalization and reaches
    get_template's path-safety check."""
    mcp = FastMCP("test", lifespan=lifespan_stub(templates_workspace))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        with pytest.raises(McpError, match="Access denied"):
            await client.read_resource("snowfakery://templates/..%2Foutside.yml")


@pytest.mark.anyio
async def test_get_template_missing(templates_workspace: WorkspacePaths) -> None:
    """Test fetching a missing template."""
    mcp = FastMCP("test", lifespan=lifespan_stub(templates_workspace))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        with pytest.raises(McpError, match="not found"):
            await client.read_resource("snowfakery://templates/nonexistent.yml")


@pytest.mark.anyio
async def test_get_template_missing_root(tmp_path: Path) -> None:
    """Test fetching a template when the templates root dir is missing."""
    root = tmp_path / "empty_workspace"
    root.mkdir()
    paths = WorkspacePaths(root=root)

    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_template_resources(mcp)

    async with Client(mcp) as client:
        with pytest.raises(McpError, match="Templates directory not found"):
            await client.read_resource("snowfakery://templates/foo.yml")
