"""Snowfakery MCP server package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .__about__ import __version__ as _source_version

__all__ = ["__version__"]


try:
    __version__ = version("snowfakery-mcp")
except PackageNotFoundError:  # pragma: no cover
    # Allows importing from a source checkout without an installed dist.
    __version__ = _source_version
