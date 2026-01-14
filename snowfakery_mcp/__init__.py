"""Snowfakery MCP server package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]


try:
    __version__ = version("snowfakery-mcp")
except PackageNotFoundError:  # pragma: no cover
    # Allows importing from a source checkout without an installed dist.
    __version__ = "0.0.0"
