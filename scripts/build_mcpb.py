#!/usr/bin/env python3
"""Build a complete .mcpb bundle for this MCP server.

This script produces a self-contained .mcpb file (a ZIP archive) that includes:

- manifest.json: Bundle metadata and entry point configuration
- server/: The complete MCP server code from snowfakery_mcp/
- lib/: All bundled Python package dependencies
- Supporting documentation (README.md, etc.)

The bundle is intended as a complete, portable distribution artifact for GitHub Releases
and can be installed and run by MCP clients that support Python bundles.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
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
    """Build a complete .mcpb ZIP bundle with server code and dependencies."""

    root = _project_root()
    meta = _project_metadata()
    resolved_version = _resolve_project_version(meta["name"], override_version)

    # The manifest.json specifies how to run the server from within the bundle
    manifest: dict[str, Any] = {
        "manifest_version": "0.3",
        "name": meta["name"],
        "version": resolved_version,
        "description": meta["description"],
        "author": {
            "name": "Composable Delivery",
            "url": "https://github.com/composable-delivery",
        },
        "repository": {
            "type": "git",
            "url": "https://github.com/composable-delivery/snowfakery-mcp.git",
        },
        "support": "https://github.com/composable-delivery/snowfakery-mcp/discussions",
        "license": "MIT OR Apache-2.0",
        "keywords": [
            "snowfakery",
            "data-generation",
            "testing",
            "mcp",
            "claude",
            "recipes",
        ],
        # Server configuration: how to run the bundled server
        "server": {
            "type": "python",
            "entry_point": "server/main.py",
        },
    }

    # Create a temporary directory for staging the bundle contents
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        server_dir = tmpdir_path / "server"
        lib_dir = tmpdir_path / "lib"

        # 1. Copy the snowfakery_mcp package into server/
        server_dir.mkdir(parents=True)
        shutil.copytree(
            root / "snowfakery_mcp",
            server_dir / "snowfakery_mcp",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )

        # 2. Create the entry point script
        entry_point = """#!/usr/bin/env python3
\"\"\"Entry point for Snowfakery MCP Server bundled in .mcpb.

This script runs the bundled MCP server with dependencies from lib/.
\"\"\"
import sys
from pathlib import Path

# Add bundled lib directory to Python path so imports work
bundle_lib = Path(__file__).parent.parent / "lib"
if bundle_lib.exists():
    sys.path.insert(0, str(bundle_lib))

# Now import and run the server
from snowfakery_mcp.server import run

if __name__ == "__main__":
    run()
"""
        (server_dir / "main.py").write_text(entry_point)
        (server_dir / "main.py").chmod(0o755)

        # 3. Bundle all dependencies using pip download
        print("Bundling Python dependencies...")
        lib_dir.mkdir(parents=True)

        # Get dependencies from pyproject.toml
        pyproject = root / "pyproject.toml"
        pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        dependencies = pyproject_data.get("project", {}).get("dependencies", [])

        # Download all wheels to lib/
        for dep in dependencies:
            # Simple approach: use pip download
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--destination-directory",
                    str(lib_dir),
                    "--no-deps",
                    dep,
                ],
                check=True,
                capture_output=True,
            )

        # 4. Create manifest.json
        manifest_path = tmpdir_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        # 5. Copy documentation files
        for filename in ("README.md", "MCP_SERVER_SPEC.md", "THIRD_PARTY_NOTICES.md"):
            src = root / filename
            if src.exists():
                shutil.copy(src, tmpdir_path / filename)

        # 6. Create the .mcpb ZIP archive
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zf:
            for file_path in tmpdir_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(tmpdir_path)
                    zf.write(str(file_path), str(arcname))

    print(f"Created bundle: {output_path}")
    print(f"  Version: {resolved_version}")
    print("  Entry point: server/main.py")
    print("  Type: python")


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
