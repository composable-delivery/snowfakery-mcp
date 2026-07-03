from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastmcp import Client, FastMCP

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.server import mcp as server_app

if TYPE_CHECKING:
    pass


def lifespan_stub(paths: WorkspacePaths, config: Config | None = None) -> Any:
    """Build a ``lifespan=`` callable yielding ``{"paths": ..., "config": ...}``.

    Phase 4 (see ``FASTMCP3_REFACTOR_PLAN.md``) moved every registered tool/
    resource to read ``paths``/``config`` from ``ctx.lifespan_context`` at
    call time instead of a closure captured at registration time. Tests that
    construct a real ``fastmcp.FastMCP("test")`` instance directly (instead of
    going through ``snowfakery_mcp.server.create_app()``) need to supply a
    minimal stand-in lifespan so that context dict is populated the same way.
    """

    resolved_config = config if config is not None else Config.from_env()

    @asynccontextmanager
    async def _lifespan(_app: FastMCP) -> AsyncIterator[dict[str, Any]]:
        yield {"paths": paths, "config": resolved_config}

    return _lifespan


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


def _resource_text(result: list[Any] | Any) -> str:
    """Extract text content from a FastMCP resource response."""
    # FastMCP returns resource content in a structured format
    if isinstance(result, list) and result:
        first: Any = result[0]
        if hasattr(first, "text"):
            return str(first.text)
        if isinstance(first, str):
            return first
    if hasattr(result, "text"):
        return str(result.text)
    if isinstance(result, str):
        return result
    raise AssertionError(f"Expected text resource contents, got {type(result)}")


def _tool_result_text(result: Any) -> str:
    """Extract text content from a FastMCP tool result."""
    # FastMCP tool results have a .data attribute with the actual content
    if hasattr(result, "data"):
        data: Any = result.data
        if isinstance(data, str):
            return data
        if isinstance(data, list) and data:
            first = data[0]
            if hasattr(first, "text"):
                return str(first.text)
            if isinstance(first, str):
                return first
        return str(data)
    if isinstance(result, str):
        return result
    raise AssertionError(f"Expected tool result with text, got {type(result)}")


@pytest.fixture
async def mcp_client() -> AsyncIterator[Client[Any]]:
    """Create a FastMCP client connected to the Snowfakery MCP server (in-memory).

    This uses FastMCP's in-memory transport for fast, reliable testing
    without spawning subprocesses.
    """
    client: Client[Any] = Client(server_app)
    async with client:
        yield client
