"""Unit-level branch coverage for tools/examples.py, driven through a real
FastMCP server instance and a real fastmcp.Client (in-memory transport) instead
of a MagicMock(spec=FastMCP) decorator-capture harness.

Calling the real, decorator-registered get_example tool via Client exercises
FastMCP's actual argument validation and exception-to-CallToolResult
conversion, including real WorkspacePaths.ensure_within() path-safety checks -
none of which a captured raw function call would exercise.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP

from conftest import lifespan_stub
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.tools.examples import register_example_tools


@pytest.mark.anyio
async def test_get_example_workspace_path(tmp_path: Path) -> None:
    """get_example reads from the real submodule examples dir inside the workspace,
    exercising the real WorkspacePaths.ensure_within() path-safety check."""
    root = tmp_path / "workspace"
    examples_dir = root / "Snowfakery" / "examples"
    examples_dir.mkdir(parents=True)
    (examples_dir / "test.yml").write_text("content")

    paths = WorkspacePaths(root=root)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_example_tools(mcp)

    async with Client(mcp) as client:
        result = await client.call_tool("get_example", {"name": "test.yml"})
        # get_example now advertises a real ExampleResult output schema (Phase
        # 6), so the client parses structured_content into a typed dataclass
        # instead of a plain dict - attribute access, not subscript.
        assert result.data.content == "content"
        assert result.data.path == str(examples_dir / "test.yml")

        missing = await client.call_tool(
            "get_example", {"name": "missing.yml"}, raise_on_error=False
        )
        assert missing.is_error is True


@pytest.mark.anyio
async def test_get_example_bundled_path_outside_workspace(tmp_path: Path) -> None:
    """get_example serves content when examples_root() resolves to a real
    filesystem Path that lives outside the configured workspace root."""
    root = tmp_path / "workspace"
    root.mkdir()
    paths = WorkspacePaths(root=root)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_example_tools(mcp)

    external_root = tmp_path / "external"
    external_root.mkdir()
    (external_root / "test.yml").write_text("external content")
    (external_root / "subdir").mkdir()

    with patch("snowfakery_mcp.tools.examples.examples_root", return_value=external_root):
        async with Client(mcp) as client:
            result = await client.call_tool("get_example", {"name": "test.yml"})
            assert result.data.content == "external content"
            assert result.data.path == "bundled:snowfakery_mcp/bundled_examples/test.yml"

            directory_result = await client.call_tool(
                "get_example", {"name": "subdir"}, raise_on_error=False
            )
            assert directory_result.is_error is True

            missing_result = await client.call_tool(
                "get_example", {"name": "missing.yml"}, raise_on_error=False
            )
            assert missing_result.is_error is True


@pytest.mark.anyio
async def test_get_example_traversable_bundled(tmp_path: Path) -> None:
    """get_example reads from the real bundled Traversable when no submodule
    examples directory exists (installed-wheel mode)."""
    paths = WorkspacePaths(root=tmp_path)
    mcp = FastMCP("test", lifespan=lifespan_stub(paths))
    register_example_tools(mcp)

    async with Client(mcp) as client:
        # test_alpha.yml ships in snowfakery_mcp/bundled_examples/.
        result = await client.call_tool("get_example", {"name": "test_alpha.yml"})
        assert len(result.data.content) > 0
        assert result.data.path == "bundled:snowfakery_mcp/bundled_examples/test_alpha.yml"

        missing_result = await client.call_tool(
            "get_example", {"name": "missing.yml"}, raise_on_error=False
        )
        assert missing_result.is_error is True
