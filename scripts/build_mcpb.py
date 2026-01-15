#!/usr/bin/env python3
"""Build a .mcpb bundle for this MCP server using the uv runtime.

This script produces a .mcpb file (a ZIP archive) that includes:

- manifest.json: Bundle metadata and entry point configuration
- server/: The complete MCP server code from snowfakery_mcp/
- pyproject.toml: Dependency declarations (uv installs these at runtime)
- Supporting documentation (README.md, etc.)

The bundle uses type: "uv" which means Claude Desktop will use uv to manage
Python dependencies automatically. This results in smaller bundles (~100KB)
compared to bundling all dependencies (~27MB).

Requirements: Users must have uv installed (e.g., `brew install uv` on macOS).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
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
        # Server configuration: use uv tool run to install and run from PyPI
        "server": {
            "type": "python",
            "entry_point": "server/main.py",
            "mcp_config": {
                "command": "uv",
                "args": [
                    "tool",
                    "run",
                    "--from",
                    f"snowfakery-mcp=={resolved_version}",
                    "snowfakery-mcp",
                ],
            },
        },
        # Declare runtime requirements
        "compatibility": {
            "runtimes": {
                "python": ">=3.10",
            },
        },
    }

    # Create a temporary directory for staging the bundle contents
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        server_dir = tmpdir_path / "server"

        # 1. Copy the snowfakery_mcp package into server/
        server_dir.mkdir(parents=True)
        shutil.copytree(
            root / "snowfakery_mcp",
            server_dir / "snowfakery_mcp",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )

        # 2. Create the entry point script
        entry_point = '''#!/usr/bin/env python3
"""Entry point for Snowfakery MCP Server bundled in .mcpb.

This script is run by Claude Desktop using the uv runtime.
Dependencies are installed automatically by uv from pyproject.toml.

Requirements:
  - uv must be installed: https://docs.astral.sh/uv/getting-started/installation
  - Install via: brew install uv (macOS) or curl -LsSf https://astral.sh/uv/install.sh | sh
"""
import sys

try:
    from snowfakery_mcp.server import run
except ImportError as e:
    print(
        f"ERROR: Failed to import snowfakery_mcp: {e}\\n"
        "\\n"
        "This usually means dependencies are not installed.\\n"
        "This server should be run via Claude Desktop with uv.\\n"
        "\\n"
        "If uv is not installed, install it first:\\n"
        "  Mac/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh\\n"
        "  Windows:   powershell -ExecutionPolicy ByPass -c \\"irm https://astral.sh/uv/install.ps1 | iex\\"\\n"
        "  Homebrew:  brew install uv\\n"
        "\\n"
        "More info: https://docs.astral.sh/uv/getting-started/installation\\n",
        file=sys.stderr,
    )
    sys.exit(1)

if __name__ == "__main__":
    run()
'''
        (server_dir / "main.py").write_text(entry_point)
        (server_dir / "main.py").chmod(0o755)

        # 3. Copy pyproject.toml (uv uses this to install dependencies at runtime)
        shutil.copy(root / "pyproject.toml", tmpdir_path / "pyproject.toml")

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
    print("  Type: uv (dependencies installed at runtime)")


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
