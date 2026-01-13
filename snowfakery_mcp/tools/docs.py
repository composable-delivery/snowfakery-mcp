from __future__ import annotations

import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_doc_tools(mcp: FastMCP, paths: WorkspacePaths) -> None:
    @mcp.tool()
    def get_schema() -> dict[str, Any]:
        """Return the Snowfakery recipe JSON schema used for authoring/validation."""

        schema_path = paths.root / "Snowfakery" / "schema" / "snowfakery_recipe.jsonschema.json"
        return {"uri": "snowfakery://schema/recipe-jsonschema", "schema": read_text_utf8(schema_path)}

    @mcp.tool()
    def search_docs(query: str, limit: int = 20) -> dict[str, Any]:
        """Search Snowfakery markdown docs for a query string and return matching lines."""

        if not query.strip():
            raise ValueError("query must be non-empty")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        docs_dir = paths.root / "Snowfakery" / "docs"
        hits: list[dict[str, Any]] = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for path in docs_dir.rglob("*.md"):
            text = read_text_utf8(path)
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    hits.append(
                        {
                            "doc": str(path.relative_to(docs_dir)).replace("\\", "/"),
                            "line": idx,
                            "snippet": line.strip(),
                        }
                    )
                    if len(hits) >= limit:
                        return {"query": query, "hits": hits, "truncated": True}

        return {"query": query, "hits": hits, "truncated": False}
