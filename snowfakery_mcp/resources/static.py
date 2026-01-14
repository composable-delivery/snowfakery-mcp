"""Static MCP resources (schema, docs, examples).

These functions are registered via FastMCP decorators, so they may appear
"unused" to static analyzers even though they are invoked at runtime.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from snowfakery_mcp.core.assets import (
    docs_root,
    examples_root,
    iter_files,
    safe_relpath,
)
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_static_resources(mcp: FastMCP, paths: WorkspacePaths) -> None:
    """Register read-only resources like schema, docs, and bundled examples."""

    @mcp.resource("snowfakery://schema/recipe-jsonschema")
    def recipe_schema_resource() -> str:
        # Prefer the Snowfakery submodule if present (dev mode), but fall back
        # to the bundled copy when installed from a wheel or when submodules
        # are not checked out in CI.
        schema_path = paths.root / "Snowfakery" / "schema" / "snowfakery_recipe.jsonschema.json"
        if schema_path.exists():
            return read_text_utf8(schema_path)

        return (
            resources.files("snowfakery_mcp.schema")
            .joinpath("snowfakery_recipe.jsonschema.json")
            .read_text(encoding="utf-8")
        )

    @mcp.resource("snowfakery://docs/index")
    def docs_index_resource() -> str:
        root = docs_root(paths)
        return read_text_utf8(root.joinpath("index.md"))

    @mcp.resource("snowfakery://docs/extending")
    def docs_extending_resource() -> str:
        root = docs_root(paths)
        return read_text_utf8(root.joinpath("extending.md"))

    @mcp.resource("snowfakery://docs/salesforce")
    def docs_salesforce_resource() -> str:
        root = docs_root(paths)
        return read_text_utf8(root.joinpath("salesforce.md"))

    @mcp.resource("snowfakery://docs/architecture")
    def docs_architecture_resource() -> str:
        root = docs_root(paths)
        return read_text_utf8(root.joinpath("arch", "ArchIndex.md"))

    @mcp.resource("snowfakery://docs/embedding")
    def docs_embedding_resource() -> str:
        root = docs_root(paths)
        return read_text_utf8(root.joinpath("embedding.md"))

    @mcp.resource("snowfakery://examples/list")
    def examples_list_resource() -> str:
        root = examples_root(paths)
        names = iter_files(root, suffixes=[".yml"])
        return json.dumps({"examples": names}, indent=2)

    @mcp.resource("snowfakery://examples/{name}")
    def example_resource(name: str) -> str:
        root = examples_root(paths)
        node: Path | Traversable
        # If the examples root is inside the configured workspace root (e.g. the
        # Snowfakery git submodule), enforce workspace/path traversal safety via
        # WorkspacePaths. If the examples root comes from package resources
        # (installed wheel), it will typically live outside the workspace root
        # and should be treated as bundled content.
        if isinstance(root, Path):
            is_workspace_dir = root.resolve().is_relative_to(paths.root)
            if not is_workspace_dir:
                rel = safe_relpath(name)
                node = root.joinpath(*rel.parts)
                if node.is_dir():
                    raise IsADirectoryError(f"Example is a directory: {name}")
                if not node.is_file():
                    raise FileNotFoundError(f"Example not found: {name}")
                return read_text_utf8(node)

            candidate = root / name
            path = paths.ensure_within(root, candidate)
            if not path.exists():
                raise FileNotFoundError(f"Example not found: {name}")
            return read_text_utf8(path)

        rel = safe_relpath(name)
        node = root.joinpath(*rel.parts)
        if node.is_dir():
            raise IsADirectoryError(f"Example is a directory: {name}")
        if not node.is_file():
            raise FileNotFoundError(f"Example not found: {name}")
        return read_text_utf8(node)
