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

    version = tag[1:]  # Remove 'v' prefix
    print(f"📌 Derived version: {version}", file=sys.stderr)
    return version


def create_and_push_tag(tag: str) -> bool:
    """Create and push a git tag."""
    if not validate_tag(tag):
        return False

    try:
        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            check=True,
        )

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
        if actual != expected_version:
            print(
                f"❌ Wheel version {actual} != expected {expected_version}",
                file=sys.stderr,
            )
            return False

        print(f"✅ Wheel version verified: {actual}")
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
            return 0 if create_and_push_tag(args.tag, args.run_tests) else 1

        elif args.command == "verify-wheel":
            return 0 if verify_wheel_version(args.wheel, args.expected) else 1

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
