"""Community template resources."""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_template_resources(mcp: FastMCP, paths: WorkspacePaths) -> None:
    """Register community recipe templates as resources."""

    def _get_templates_root() -> Path | None:
        # Check for the templates directory in the workspace root
        candidate = paths.root / "Snowfakery-Recipe-Templates" / "snowfakery_samples"
        if candidate.exists() and candidate.is_dir():
            return candidate
        return None

    @mcp.resource("snowfakery://templates/list")
    def list_templates() -> str:
        root = _get_templates_root()
        if not root:
            return json.dumps({"templates": [], "note": "Templates directory not found"})

        # Collect .yml files recursively
        # We manually iterate because iter_files might be shallow or have specific logic
        # Ideally we want relative paths like 'EDA/Account_EDA.recipe.yml'

        files = []
        for path in root.rglob("*.yml"):
            if path.is_file():
                rel_path = path.relative_to(root)
                files.append(str(rel_path))

        return json.dumps({"templates": sorted(files)}, indent=2)

    @mcp.resource("snowfakery://templates/{path_str}")
    def get_template(path_str: str) -> str:
        root = _get_templates_root()
        if not root:
            raise FileNotFoundError("Templates directory not found")

        # Security check: ensure the requested path is inside the templates root
        # path_str might contain forward slashes even on Windows due to URI format

        # Normative path construction
        target_path = (root / path_str).resolve()

        try:
            target_path.relative_to(root.resolve())
        except ValueError as e:
            raise ValueError(f"Access denied: {path_str} escapes templates directory") from e

        if not target_path.exists():
            raise FileNotFoundError(f"Template not found: {path_str}")

        if not target_path.is_file():
            raise IsADirectoryError(f"Path is a directory: {path_str}")

        return read_text_utf8(target_path)
