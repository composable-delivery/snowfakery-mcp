"""Example-related MCP tools.

Tool functions are registered via FastMCP decorators, so they may appear
"unused" to static analyzers even though they are invoked at runtime.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from snowfakery_mcp.core.assets import examples_root, iter_files, safe_relpath
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_example_tools(mcp: FastMCP, paths: WorkspacePaths) -> None:
    """Register tools for listing and fetching bundled Snowfakery examples."""

    @mcp.tool(tags={"discovery", "examples"})
    def list_examples(prefix: str | None = None) -> dict[str, Any]:
        """List available Snowfakery example recipe files.

        Returns a list of example recipe filenames from the bundled examples.
        Use prefix to filter results (e.g., "salesforce" for Salesforce examples).
        """

        root = examples_root(paths)
        names = iter_files(root, suffixes=[".yml"])
        if prefix is not None:
            names = [n for n in names if n.startswith(prefix)]
        return {"examples": names}

    @mcp.tool(tags={"discovery", "examples"})
    def get_example(name: str) -> dict[str, Any]:
        """Fetch a Snowfakery example recipe by name.

        Returns the full text of the specified example recipe.
        Use list_examples first to see available examples.
        """

        root = examples_root(paths)
        node: Path | Traversable
        if isinstance(root, Path):
            is_workspace_dir = root.resolve().is_relative_to(paths.root)
            if not is_workspace_dir:
                rel = safe_relpath(name)
                node = root.joinpath(*rel.parts)
                if node.is_dir():
                    raise IsADirectoryError(f"Example is a directory: {name}")
                if not node.is_file():
                    raise FileNotFoundError(f"Example not found: {name}")
                return {
                    "name": name,
                    "path": f"bundled:snowfakery_mcp/bundled_examples/{rel}",
                    "text": read_text_utf8(node),
                }

            path = paths.ensure_within(root, root / name)
            if not path.exists():
                raise FileNotFoundError(f"Example not found: {name}")
            return {"name": name, "path": str(path), "text": read_text_utf8(path)}

        rel = safe_relpath(name)
        node = root.joinpath(*rel.parts)
        if node.is_dir():
            raise IsADirectoryError(f"Example is a directory: {name}")
        if not node.is_file():
            raise FileNotFoundError(f"Example not found: {name}")
        return {
            "name": name,
            "path": f"bundled:snowfakery_mcp/bundled_examples/{rel}",
            "text": read_text_utf8(node),
        }
