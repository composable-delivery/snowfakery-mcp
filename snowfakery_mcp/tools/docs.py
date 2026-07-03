from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from snowfakery_mcp.core.assets import docs_root, iter_files
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8
from snowfakery_mcp.core.types import DocSearchHit, DocsSearchResult

_DISCOVERY_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, idempotentHint=True)


def register_doc_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        tags={"discovery", "schema"},
        annotations=_DISCOVERY_ANNOTATIONS,
        version="1",
    )
    def get_schema(ctx: Context) -> dict[str, Any]:
        """Return the Snowfakery recipe JSON schema.

        Use this schema to understand the structure of valid recipes
        and for validation purposes.
        """

        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        schema_path = paths.root / "Snowfakery" / "schema" / "snowfakery_recipe.jsonschema.json"
        if schema_path.exists():
            schema_text = read_text_utf8(schema_path)
        else:
            schema_text = (
                resources.files("snowfakery_mcp.schema")
                .joinpath("snowfakery_recipe.jsonschema.json")
                .read_text(encoding="utf-8")
            )

        return {
            "uri": "snowfakery://schema/recipe-jsonschema",
            "schema": json.loads(schema_text),
        }

    @mcp.tool(
        tags={"discovery", "docs"},
        annotations=_DISCOVERY_ANNOTATIONS,
        version="1",
    )
    def search_docs(query: str, limit: int = 20, *, ctx: Context) -> DocsSearchResult:
        """Search Snowfakery documentation for a query string.

        Returns matching lines from the markdown documentation.
        Useful for finding specific syntax, features, or examples.
        """

        if not query.strip():
            raise ValueError("query must be non-empty")
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if limit > 200:
            raise ValueError("limit must be <= 200")

        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        docs_dir = docs_root(paths)
        hits: list[DocSearchHit] = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for doc in iter_files(docs_dir, suffixes=[".md"]):
            path = docs_dir.joinpath(*doc.split("/"))
            text = read_text_utf8(path)
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    hits.append(
                        {
                            "doc": doc,
                            "line": idx,
                            "snippet": line.strip(),
                        }
                    )
                    if len(hits) >= limit:
                        return {"query": query, "hits": hits, "truncated": True}

        return {"query": query, "hits": hits, "truncated": False}
