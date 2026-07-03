from __future__ import annotations

import json

from fastmcp import Context, FastMCP
from fastmcp.resources import ResourceContent, ResourceResult

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8

# Snowfakery output formats that are genuinely binary (see snowfakery.api.file_extensions)
# and would crash on a forced UTF-8 decode. Every other format (txt/json/sql/dot/svg/yml/
# ps/csv) is plain text and keeps the existing text-reading path below.
_BINARY_MIME_TYPES = {
    ".png": "image/png",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".svgz": "image/svg+xml",
}


def register_run_resources(mcp: FastMCP) -> None:
    @mcp.resource("snowfakery://runs/{run_id}/{artifact}")
    def run_artifact_resource(run_id: str, artifact: str, ctx: Context) -> str | ResourceResult:
        paths: WorkspacePaths = ctx.lifespan_context["paths"]
        run_dir = paths.ensure_within_workspace(paths.runs_root() / run_id)
        path = paths.ensure_within(run_dir, run_dir / artifact)

        if path.is_dir():
            entries = sorted(
                str(p.relative_to(run_dir)).replace("\\", "/")
                for p in path.rglob("*")
                if p.is_file()
            )
            return json.dumps({"files": entries}, indent=2)

        mime_type = _BINARY_MIME_TYPES.get(path.suffix.lower())
        if mime_type is not None:
            return ResourceResult([ResourceContent(path.read_bytes(), mime_type=mime_type)])

        return read_text_utf8(path)
