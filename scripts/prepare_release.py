#!/usr/bin/env python
"""Release asset preparation script.

Handles:
- Third-party notices generation
- MCPB bundle creation
- PyPI distribution preparation
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"▶ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, text=True)


def generate_third_party_notices() -> None:
    """Generate third-party notices from dependencies."""
    print("📋 Generating third-party notices...")
    run_command(["uv", "run", "python", "scripts/generate_third_party_notices.py"])


def build_distributions() -> None:
    """Build wheel and sdist distributions."""
    print("🔨 Building distributions...")
    run_command(["uv", "build"])


def prepare_release_assets(version: str | None = None) -> None:
    """Prepare release assets directory."""
    print("📦 Preparing release assets...")

    assets_dir = Path("release-assets")
    assets_dir.mkdir(exist_ok=True)

    # Copy third-party notices
    notices_src = Path("THIRD_PARTY_NOTICES.md")
    if notices_src.exists():
        run_command(["cp", str(notices_src), str(assets_dir / "THIRD_PARTY_NOTICES.md")])

    # Build MCPB bundle
    mcpb_filename = "snowfakery-mcp-dev.mcpb"
    if version:
        mcpb_filename = f"snowfakery-mcp-{version}.mcpb"

    print(f"🔗 Building MCPB bundle: {mcpb_filename}")
    cmd = ["python", "scripts/build_mcpb.py", "--output", str(assets_dir / mcpb_filename)]
    if version:
        cmd.extend(["--version", version])
    run_command(cmd)


def prepare_pypi_dist() -> None:
    """Prepare PyPI distribution directory."""
    print("📤 Preparing PyPI distribution...")

    dist_dir = Path("pypi-dist")
    dist_dir.mkdir(exist_ok=True)

    run_command(["cp"] + list(Path("dist").glob("*.whl")) + [str(dist_dir)])
    run_command(["cp"] + list(Path("dist").glob("*.tar.gz")) + [str(dist_dir)])


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
        help="Version string for MCPB bundle (e.g., 0.2.0)",
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
        if not args.skip_notices:
            generate_third_party_notices()

        if not args.skip_tests:
            run_tests(ignore_snowfakery=args.ignore_snowfakery)

        if not args.skip_build:
            build_distributions()

        prepare_release_assets(version=args.version)
        prepare_pypi_dist()

        print("✅ Release preparation complete!")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
