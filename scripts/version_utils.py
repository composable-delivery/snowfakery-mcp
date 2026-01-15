#!/usr/bin/env python
"""Version and tag validation utilities.

Handles:
- Tag format validation (vX.Y.Z)
- Version derivation from git tags
- Git operations (tag creation, pushing)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from packaging.version import InvalidVersion, Version


def validate_tag(tag: str) -> bool:
    """Validate tag format (vX.Y.Z)."""
    if not tag:
        print("❌ Tag is empty", file=sys.stderr)
        return False

    pattern = r"^v(?P<ver>\d+\.\d+\.\d+(?:[a-zA-Z0-9\.\-]+)?)$"
    if not re.match(pattern, tag):
        print(f"❌ Tag '{tag}' does not match vX.Y.Z format", file=sys.stderr)
        return False

    print(f"✅ Tag format valid: {tag}", file=sys.stderr)
    return True


def derive_version_from_tag(tag: str) -> str | None:
    """Derive version string from git tag (strip 'v' prefix)."""
    if not validate_tag(tag):
        return None

    raw_version = tag[1:]  # Remove 'v' prefix
    try:
        normalized = str(Version(raw_version))
    except InvalidVersion:
        print(
            f"❌ Tag '{tag}' contains an invalid PEP 440 version: '{raw_version}'",
            file=sys.stderr,
        )
        return None

    print(f"📌 Derived version: {normalized}", file=sys.stderr)
    return normalized


def _update_version_file(version: str) -> bool:
    """Update the version in snowfakery_mcp/__about__.py.

    Returns True if the file was changed.
    """

    about_path = Path(__file__).resolve().parents[1] / "snowfakery_mcp" / "__about__.py"
    if not about_path.exists():
        print(f"❌ Missing version file: {about_path}", file=sys.stderr)
        return False

    content = about_path.read_text(encoding="utf-8")
    new_content, count = re.subn(
        r'^__version__\s*=\s*"[^"]+"\s*$',
        f'__version__ = "{version}"',
        content,
        flags=re.MULTILINE,
    )
    if count != 1:
        print("❌ Could not update __version__ in __about__.py", file=sys.stderr)
        return False

    if new_content == content:
        return False

    about_path.write_text(new_content, encoding="utf-8")
    return True


def _git_is_detached_head() -> bool:
    cp = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return cp.returncode != 0


def create_and_push_tag(tag: str, run_tests: bool = False) -> bool:
    """Create and push a release commit (version bump) and tag.

    This keeps the tag pointing at a commit whose packaged version matches the tag,
    which makes wheel/sdist builds deterministic.
    """
    if not validate_tag(tag):
        return False

    try:
        if _git_is_detached_head():
            print(
                "❌ Refusing to create a release tag from detached HEAD.",
                file=sys.stderr,
            )
            return False

        version = derive_version_from_tag(tag)
        if not version:
            return False

        if run_tests:
            print("🧪 Running tests before tagging...")
            subprocess.run(["uv", "run", "pytest", "--ignore=Snowfakery"], check=True)

        changed = _update_version_file(version)

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            check=True,
        )

        if changed:
            subprocess.run(
                ["git", "add", "snowfakery_mcp/__about__.py"],
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Release {tag}"],
                check=True,
            )
            print("📤 Pushing release commit to origin")
            subprocess.run(["git", "push", "origin", "HEAD"], check=True)
        else:
            print("ℹ️  Version file already matches; no commit created")

        # Check if tag already exists
        result = subprocess.run(
            ["git", "rev-parse", tag],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"ℹ️  Tag already exists locally: {tag}")
        else:
            print(f"📌 Creating tag: {tag}")
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", tag],
                check=True,
            )

        # Push tag
        print(f"📤 Pushing tag to origin: {tag}")
        subprocess.run(
            ["git", "push", "origin", f"refs/tags/{tag}"],
            check=True,
        )

        print(f"✅ Tag created and pushed: {tag}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"❌ OS error during git operation: {e}", file=sys.stderr)
        return False


def verify_wheel_version(wheel_path: str, expected_version: str) -> bool:
    """Verify wheel METADATA version matches expected version."""
    import zipfile

    print(f"🔍 Verifying wheel version: {wheel_path}")

    try:
        with zipfile.ZipFile(wheel_path) as zf:
            metas = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
            if not metas:
                print("❌ Wheel missing METADATA", file=sys.stderr)
                return False

            metadata = zf.read(metas[0]).decode("utf-8", errors="replace")

        m = re.search(r"^Version:\s*(.+)\s*$", metadata, flags=re.MULTILINE)
        if not m:
            print("❌ Could not find Version in wheel METADATA", file=sys.stderr)
            return False

        actual = m.group(1).strip()
        try:
            actual_norm = str(Version(actual))
            expected_norm = str(Version(expected_version))
        except InvalidVersion as e:
            print(f"❌ Invalid version during comparison: {e}", file=sys.stderr)
            return False

        if actual_norm != expected_norm:
            print(
                f"❌ Wheel version {actual_norm} != expected {expected_norm}",
                file=sys.stderr,
            )
            return False

        print(f"✅ Wheel version verified: {actual_norm}")
        return True

    except Exception as e:
        print(f"❌ Error verifying wheel: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Version and tag utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate tag
    validate_parser = subparsers.add_parser("validate", help="Validate tag format")
    validate_parser.add_argument("tag", help="Tag to validate (e.g., v0.2.0)")

    # Derive version
    derive_parser = subparsers.add_parser("derive", help="Derive version from tag")
    derive_parser.add_argument("tag", help="Tag to derive from (e.g., v0.2.0)")

    # Create and push tag
    tag_parser = subparsers.add_parser("create", help="Create and push tag")
    tag_parser.add_argument("tag", help="Tag to create (e.g., v0.2.0)")
    tag_parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests before creating tag",
    )

    # Verify wheel
    wheel_parser = subparsers.add_parser("verify-wheel", help="Verify wheel version")
    wheel_parser.add_argument("wheel", help="Path to wheel file")
    wheel_parser.add_argument("expected", help="Expected version (e.g., 0.2.0)")

    args = parser.parse_args()

    try:
        if args.command == "validate":
            return 0 if validate_tag(args.tag) else 1

        elif args.command == "derive":
            version = derive_version_from_tag(args.tag)
            if version:
                print(version)
                return 0
            return 1

        elif args.command == "create":
            return 0 if create_and_push_tag(args.tag, run_tests=args.run_tests) else 1

        elif args.command == "verify-wheel":
            return 0 if verify_wheel_version(args.wheel, args.expected) else 1

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
