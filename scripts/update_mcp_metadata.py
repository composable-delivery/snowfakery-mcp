#!/usr/bin/env python
"""Update MCP metadata files with a given version.

Keeps version-update logic out of GitHub Actions YAML.

Updates:
- server.json: top-level "version" and any "packages[*].version"
- manifest.json: "version" (if file exists)

This script intentionally uses only the Python standard library so it can run
in CI without installing project dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to parse JSON: {path}") from exc


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _update_server_json(path: Path, version: str) -> bool:
    data = _read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object at top-level: {path}")

    changed = False

    if data.get("version") != version:
        data["version"] = version
        changed = True

    packages = data.get("packages")
    if isinstance(packages, list):
        for package in packages:
            if isinstance(package, dict) and package.get("version") != version:
                package["version"] = version
                changed = True

    if changed:
        _write_json(path, data)

    return changed


def _update_manifest_json(path: Path, version: str) -> bool:
    if not path.exists():
        return False

    data = _read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object at top-level: {path}")

    if data.get("version") == version:
        return False

    data["version"] = version
    _write_json(path, data)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update MCP metadata versions")
    parser.add_argument(
        "version",
        help="Version to set (e.g., 0.2.0, 0.2.0b0)",
    )
    parser.add_argument(
        "--skip-server-json",
        action="store_true",
        help="Do not update server.json",
    )
    parser.add_argument(
        "--skip-manifest-json",
        action="store_true",
        help="Do not update manifest.json",
    )
    parser.add_argument(
        "--server-json",
        default="server.json",
        help="Path to server.json (default: server.json)",
    )
    parser.add_argument(
        "--manifest-json",
        default="manifest.json",
        help="Path to manifest.json (default: manifest.json)",
    )

    args = parser.parse_args()

    repo_root = Path.cwd()
    server_json_path = repo_root / args.server_json
    manifest_json_path = repo_root / args.manifest_json

    try:
        server_changed = False
        manifest_changed = False

        if not args.skip_server_json:
            server_changed = _update_server_json(server_json_path, args.version)

        if not args.skip_manifest_json:
            manifest_changed = _update_manifest_json(manifest_json_path, args.version)

        print(
            "Updated MCP metadata: "
            f"server.json={'changed' if server_changed else 'unchanged'}, "
            f"manifest.json={'changed' if manifest_changed else 'unchanged'}",
            file=sys.stderr,
        )
        return 0

    except FileNotFoundError:
        missing = server_json_path if not args.skip_server_json else manifest_json_path
        print(f"ERROR: Missing required file: {missing}", file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
