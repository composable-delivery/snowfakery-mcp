#!/usr/bin/env python
"""Release asset preparation script.

Handles:
- Third-party notices generation
- PyPI distribution preparation

Note: MCPB bundle is now built by a separate GitHub Actions workflow
(build-mcpb.yml) for better reusability across CI and release workflows.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Union

from packaging.version import InvalidVersion, Version

CmdPart = Union[str, Path]  # noqa: UP007


def run_command(cmd: Iterable[CmdPart], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command.

    Accepts both strings and Paths (converted to strings) to avoid type errors.
    """
    cmd_list = [str(c) for c in cmd]
    print(f"▶ {' '.join(cmd_list)}")
    return subprocess.run(cmd_list, check=check, text=True)


def generate_third_party_notices() -> None:
    """Generate third-party notices from dependencies."""
    print("📋 Generating third-party notices...")
    run_command(["uv", "run", "python", "scripts/generate_third_party_notices.py"])


def build_distributions() -> None:
    """Build wheel and sdist distributions."""
    print("🔨 Building distributions...")
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    run_command(["uv", "build"])


def normalize_version(version: str) -> str:
    """Normalize a version string to canonical PEP 440 form."""
    try:
        return str(Version(version))
    except InvalidVersion as e:
        raise ValueError(f"Invalid PEP 440 version '{version}': {e}") from e


@contextmanager
def temporary_source_version(version: str):
    """Temporarily set snowfakery_mcp/__about__.py __version__ for builds."""
    about_path = Path("snowfakery_mcp") / "__about__.py"
    if not about_path.exists():
        raise FileNotFoundError(f"Missing version file: {about_path}")

    original = about_path.read_text(encoding="utf-8")
    normalized = normalize_version(version)

    updated, count = re.subn(
        r'^__version__\s*=\s*"[^"]+"\s*$',
        f'__version__ = "{normalized}"',
        original,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("Could not locate a single __version__ assignment in __about__.py")

    about_path.write_text(updated, encoding="utf-8")
    try:
        yield normalized
    finally:
        about_path.write_text(original, encoding="utf-8")


def prepare_release_assets() -> None:
    """Prepare release assets directory.

    Note: MCPB bundle is now built by a separate GitHub Actions workflow
    (build-mcpb.yml) and is not included here.
    """
    print("📦 Preparing release assets...")

    assets_dir = Path("release-assets")
    assets_dir.mkdir(exist_ok=True)

    # Copy third-party notices
    notices_src = Path("THIRD_PARTY_NOTICES.md")
    if notices_src.exists():
        run_command(["cp", str(notices_src), str(assets_dir / "THIRD_PARTY_NOTICES.md")])


def prepare_pypi_dist(version: str | None = None) -> None:
    """Prepare PyPI distribution directory."""
    print("📤 Preparing PyPI distribution...")

    dist_dir = Path("pypi-dist")
    dist_dir.mkdir(exist_ok=True)

    if version:
        normalized = normalize_version(version)
        wheels = list(Path("dist").glob(f"*{normalized}*.whl"))
        sdists = list(Path("dist").glob(f"*{normalized}*.tar.gz"))
    else:
        wheels = list(Path("dist").glob("*.whl"))
        sdists = list(Path("dist").glob("*.tar.gz"))

    if wheels:
        run_command(["cp", *wheels, dist_dir])
    if sdists:
        run_command(["cp", *sdists, dist_dir])


def run_tests(ignore_snowfakery: bool = False) -> None:
    """Run test suite."""
    print("🧪 Running tests...")

    cmd = ["uv", "run", "pytest", "-v", "--tb=short"]
    if ignore_snowfakery:
        cmd.append("--ignore=Snowfakery")

    run_command(cmd)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Prepare release assets and distributions")
    parser.add_argument(
        "--version",
        help="Version string (PEP 440) used for wheel/sdist + MCPB bundle (e.g., 0.2.0, 0.2.0b0)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests",
    )
    parser.add_argument(
        "--ignore-snowfakery",
        action="store_true",
        help="Ignore Snowfakery directory when running tests",
    )
    parser.add_argument(
        "--skip-notices",
        action="store_true",
        help="Skip generating third-party notices",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building distributions",
    )

    args = parser.parse_args()

    try:
        normalized_version = normalize_version(args.version) if args.version else None

        if not args.skip_notices:
            generate_third_party_notices()

        if not args.skip_tests:
            run_tests(ignore_snowfakery=args.ignore_snowfakery)

        if not args.skip_build and normalized_version:
            with temporary_source_version(normalized_version):
                build_distributions()
        elif not args.skip_build:
            build_distributions()

        prepare_release_assets()
        prepare_pypi_dist(version=normalized_version)

        print("✅ Release preparation complete!")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
