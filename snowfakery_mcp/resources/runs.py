from __future__ import annotations

import json

from fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.text import read_text_utf8


def register_run_resources(mcp: FastMCP, paths: WorkspacePaths) -> None:
    @mcp.resource("snowfakery://runs/{run_id}/{artifact}")
    def run_artifact_resource(run_id: str, artifact: str) -> str:
        run_dir = paths.ensure_within_workspace(paths.runs_root() / run_id)
        path = paths.ensure_within(run_dir, run_dir / artifact)

        if path.is_dir():
            entries = sorted(
                str(p.relative_to(run_dir)).replace("\\", "/")
                for p in path.rglob("*")
                if p.is_file()
            )
            return json.dumps({"files": entries}, indent=2)

        return read_text_utf8(path)
