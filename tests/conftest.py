from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def pytest_addoption(parser: pytest.Parser) -> None:
    # Convenience flag: users sometimes try `pytest --coverage`.
    # pytest-cov uses `--cov`, so we alias `--coverage` to a basic --cov setup.
    parser.addoption(
        "--coverage",
        action="store_true",
        default=False,
        help="Alias for enabling pytest-cov with a sensible default (--cov=.).",
    )


def pytest_configure(config: pytest.Config) -> None:
    if not getattr(config.option, "coverage", False):
        return

    # Only do anything if pytest-cov is installed.
    if not config.pluginmanager.hasplugin("pytest_cov"):
        raise pytest.UsageError(
            "--coverage requires pytest-cov. Install dev deps or run `uv sync --group dev`."
        )

    # pytest-cov registers these options; set defaults if user didn't specify.
    if not getattr(config.option, "cov_source", None):
        config.option.cov_source = [str(Path.cwd())]

    if not getattr(config.option, "cov_report", None):
        config.option.cov_report = ["term-missing"]


def _resource_text(result: Any) -> str:
    """Extract text content from an MCP resource response."""
    contents = getattr(result, "contents", None)
    assert isinstance(contents, list) and contents, "Expected non-empty resource contents"
    first = cast(Any, contents[0])
    text = getattr(first, "text", None)
    assert isinstance(text, str), "Expected text resource contents"
    return text


def _tool_payload_text(result: Any) -> str:
    """Extract text content from an MCP tool result."""
    content = getattr(result, "content", None)
    assert isinstance(content, list) and content, "Expected non-empty tool result"
    first = cast(Any, content[0])
    text = getattr(first, "text", None)
    assert isinstance(text, str), "Expected text tool result"
    return text


@pytest.fixture
async def mcp_session() -> AsyncIterator[ClientSession]:
    """Create an MCP session connected to the Snowfakery MCP server."""
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
