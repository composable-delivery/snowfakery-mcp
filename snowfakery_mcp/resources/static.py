from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_static_resources(mcp: FastMCP, paths: WorkspacePaths) -> None:
    @mcp.resource("snowfakery://schema/recipe-jsonschema")
    def recipe_schema_resource() -> str:
        schema_path = paths.root / "Snowfakery" / "schema" / "snowfakery_recipe.jsonschema.json"
        return read_text_utf8(schema_path)

    @mcp.resource("snowfakery://docs/index")
    def docs_index_resource() -> str:
        return read_text_utf8(paths.root / "Snowfakery" / "docs" / "index.md")

    @mcp.resource("snowfakery://docs/extending")
    def docs_extending_resource() -> str:
        return read_text_utf8(paths.root / "Snowfakery" / "docs" / "extending.md")

    @mcp.resource("snowfakery://docs/salesforce")
    def docs_salesforce_resource() -> str:
        return read_text_utf8(paths.root / "Snowfakery" / "docs" / "salesforce.md")

    @mcp.resource("snowfakery://docs/architecture")
    def docs_architecture_resource() -> str:
        return read_text_utf8(paths.root / "Snowfakery" / "docs" / "arch" / "ArchIndex.md")

    @mcp.resource("snowfakery://examples/list")
    def examples_list_resource() -> str:
        examples_dir = paths.root / "Snowfakery" / "examples"
        names = sorted(
            str(p.relative_to(examples_dir)).replace("\\", "/")
            for p in examples_dir.rglob("*.yml")
        )
        return json.dumps({"examples": names}, indent=2)

    @mcp.resource("snowfakery://examples/{name}")
    def example_resource(name: str) -> str:
        examples_dir = paths.root / "Snowfakery" / "examples"
        candidate = examples_dir / name
        path = paths.ensure_within_workspace(candidate)
        if not path.exists():
            raise FileNotFoundError(f"Example not found: {name}")
        return read_text_utf8(path)
