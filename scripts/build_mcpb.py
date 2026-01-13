#!/usr/bin/env python3
"""Build an experimental .mcpb bundle for this MCP server.

There is not (yet) a universally adopted standard for "mcpb" bundles across all
MCP clients. This script produces a single file with a .mcpb extension that is
just a ZIP archive containing:

- manifest.json: minimal metadata and a recommended launch command
- README.md / MCP_SERVER_SPEC.md
- claude_desktop_config.json: an example Claude Desktop config snippet

The bundle is intended as a convenience artifact to attach to GitHub Releases.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _project_metadata() -> dict[str, str]:
    # Parse pyproject.toml without extra deps (Python 3.11+).
    import tomllib

    pyproject = _project_root() / "pyproject.toml"
    data = tomllib.loads(_read_text(pyproject))
    project = data.get("project", {})
    name = str(project.get("name", ""))
    version = str(project.get("version", ""))
    description = str(project.get("description", ""))
    return {"name": name, "version": version, "description": description}


def build_bundle(output_path: Path) -> None:
    root = _project_root()
    meta = _project_metadata()

    # A pragmatic default: installing from PyPI (or a wheel) then running the console script.
    # Most MCP desktop clients can run an arbitrary command.
    recommended_command = "snowfakery-mcp"

    manifest = {
        "bundle_format": "experimental",
        "type": "mcp-server",
        "name": meta["name"],
        "version": meta["version"],
        "description": meta["description"],
        "python": {
            "package": meta["name"],
            "recommended_install": f"pipx install {meta['name']}=={meta['version']}",
        },
        "launch": {
            "command": recommended_command,
            "args": [],
            "env": {
                "SNOWFAKERY_MCP_WORKSPACE_ROOT": "${workspaceRoot}",
            },
            "transport": "stdio",
        },
    }

    claude_desktop_config = {
        "mcpServers": {
            "snowfakery": {
                "command": recommended_command,
                "args": [],
                "env": {
                    # Update this to the path you want Snowfakery to treat as the workspace root.
                    "SNOWFAKERY_MCP_WORKSPACE_ROOT": "${workspaceRoot}",
                },
            }
        }
    }

    files_to_include: list[tuple[Path, str]] = []
    for rel in ("README.md", "MCP_SERVER_SPEC.md"):
        p = root / rel
        if p.exists():
            files_to_include.append((p, rel))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        zf.writestr(
            "claude_desktop_config.json",
            json.dumps(claude_desktop_config, indent=2) + "\n",
        )
        for src, arcname in files_to_include:
            zf.write(src, arcname)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        required=True,
        help="Output .mcpb file path (a ZIP archive with .mcpb extension)",
    )
    args = parser.parse_args()

    out = Path(args.output)
    if out.suffix != ".mcpb":
        # Keep it obvious to users what this is.
        out = out.with_suffix(out.suffix + ".mcpb")

    build_bundle(out)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
