from __future__ import annotations

from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_example_tools(mcp: FastMCP, paths: WorkspacePaths) -> None:
    @mcp.tool()
    def list_examples(prefix: Optional[str] = None) -> dict[str, Any]:
        """List available Snowfakery example recipe files under Snowfakery/examples."""

        examples_dir = paths.root / "Snowfakery" / "examples"
        names: list[str] = []
        for p in examples_dir.rglob("*.yml"):
            rel = str(p.relative_to(examples_dir)).replace("\\", "/")
            if prefix is not None and not rel.startswith(prefix):
                continue
            names.append(rel)
        return {"examples": sorted(names)}

    @mcp.tool()
    def get_example(name: str) -> dict[str, Any]:
        """Fetch a Snowfakery example recipe by relative path and return its text."""

        examples_dir = paths.root / "Snowfakery" / "examples"
        path = paths.ensure_within_workspace(examples_dir / name)
        if not path.exists():
            raise FileNotFoundError(f"Example not found: {name}")
        return {"name": name, "path": str(path), "text": read_text_utf8(path)}
