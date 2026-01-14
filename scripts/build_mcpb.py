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
import re
import subprocess
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as dist_version
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile


def _read_text(path: Path) -> str:
    """Read UTF-8 text from disk."""
    return path.read_text(encoding="utf-8")


def _project_root() -> Path:
    """Return the repository root (one level above scripts/)."""
    return Path(__file__).resolve().parents[1]


def _project_metadata() -> dict[str, str]:
    """Extract minimal project metadata from pyproject.toml."""
    pyproject = _project_root() / "pyproject.toml"
    data = tomllib.loads(_read_text(pyproject))
    project = data.get("project", {})
    name = str(project.get("name", ""))
    description = str(project.get("description", ""))
    return {"name": name, "description": description}


def _git_describe_version(root: Path) -> str | None:
    """Best-effort version from git tags (expects tags like vX.Y.Z)."""
    try:
        cp = subprocess.run(
            ["git", "-C", str(root), "describe", "--tags", "--dirty", "--always"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    desc = cp.stdout.strip()
    if not desc:
        return None

    # Prefer a clean vX.Y.Z tag when present.
    m = re.match(r"^v(?P<ver>\d+\.\d+\.\d+(?:[a-zA-Z0-9\.\-]+)?)$", desc)
    if m:
        return m.group("ver")
    return None


def _resolve_project_version(project_name: str, override: str | None) -> str:
    if override:
        return override

    try:
        return dist_version(project_name)
    except PackageNotFoundError:
        pass

    return _git_describe_version(_project_root()) or "0.0.0"


def _is_reasonable_pep440(version_str: str) -> bool:
    # Good enough for our use: allow common semver-ish + pre/dev local suffixes.
    return bool(re.match(r"^\d+\.\d+\.\d+(?:[a-zA-Z0-9\.\-]+)?$", version_str))


def build_bundle(output_path: Path, *, override_version: str | None = None) -> None:
    """Build a .mcpb ZIP bundle at the requested output path."""
    root = _project_root()
    meta = _project_metadata()
    resolved_version = _resolve_project_version(meta["name"], override_version)

    # A pragmatic default: installing from PyPI (or a wheel) then running the console script.
    # Most MCP desktop clients can run an arbitrary command.
    recommended_command = "snowfakery-mcp"

    if _is_reasonable_pep440(resolved_version):
        recommended_install = f"pipx install {meta['name']}=={resolved_version}"
    else:
        recommended_install = f"pipx install {meta['name']}"

    manifest: dict[str, Any] = {
        "bundle_format": "experimental",
        "type": "mcp-server",
        "name": meta["name"],
        "version": resolved_version,
        "description": meta["description"],
        "python": {
            "package": meta["name"],
            "recommended_install": recommended_install,
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

    claude_desktop_config: dict[str, Any] = {
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
    for rel in ("README.md", "MCP_SERVER_SPEC.md", "THIRD_PARTY_NOTICES.md"):
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
    """CLI entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        required=True,
        help="Output .mcpb file path (a ZIP archive with .mcpb extension)",
    )
    parser.add_argument(
        "--version",
        required=False,
        default=None,
        help="Override bundle version (normally resolved from package metadata or git tags)",
    )
    args = parser.parse_args()

    out = Path(args.output)
    if out.suffix != ".mcpb":
        # Keep it obvious to users what this is.
        out = out.with_suffix(out.suffix + ".mcpb")

    build_bundle(out, override_version=args.version)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
