#!/usr/bin/env python
"""Local workflow validation script.

Validates GitHub Actions workflow YAML without requiring package build.
For testing scripts directly, use:
  python scripts/version_utils.py --help
  python scripts/prepare_release.py --help
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML not found. Install with: uv pip add pyyaml")
    sys.exit(1)


def validate_yaml(file_path: Path) -> bool:
    """Validate YAML syntax."""
    print(f"🔍 Validating YAML: {file_path.name}")
    try:
        with open(file_path) as f:
            yaml.safe_load(f)
        print(f"✅ YAML valid: {file_path.name}")
        return True
    except yaml.YAMLError as e:
        print(f"❌ YAML error in {file_path.name}: {e}")
        return False


def check_script_directly(script_path: str) -> bool:
    """Check script directly with python -m."""
    print(f"🔍 Testing {script_path} --help")
    try:
        result = subprocess.run(
            ["python", script_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "usage:" in result.stdout.lower():
            print(f"✅ {Path(script_path).name} help working")
            return True
        else:
            print(f"❌ {Path(script_path).name} help failed")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error testing {script_path}: {e}")
        return False


def validate_workflows() -> bool:
    """Validate all workflow YAML files."""
    print("\n🔄 Validating workflow files:\n")

    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        return False

    yaml_files = sorted(list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml")))

    if not yaml_files:
        print("❌ No workflow files found")
        return False

    all_valid = True
    for workflow_file in yaml_files:
        if not validate_yaml(workflow_file):
            all_valid = False

    return all_valid


def check_scripts() -> bool:
    """Check that scripts have working --help."""
    print("\n📝 Testing scripts:\n")

    scripts = [
        "scripts/version_utils.py",
        "scripts/prepare_release.py",
    ]

    all_working = True
    for script in scripts:
        if not check_script_directly(script):
            all_working = False

    return all_working


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions workflows and test scripts locally"
    )
    parser.add_argument(
        "--workflows-only",
        action="store_true",
        help="Only validate workflow YAML files",
    )
    parser.add_argument(
        "--scripts-only",
        action="store_true",
        help="Only test scripts",
    )

    args = parser.parse_args()

    try:
        results = []

        if not args.scripts_only:
            results.append(("Workflow YAML validation", validate_workflows()))

        if not args.scripts_only:
            results.append(("Script validation", check_scripts()))

        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        all_passed = True
        for name, passed in results:
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n✅ All validation checks passed!")
            print("\n📋 To test workflows without committing:")
            print("   • Review changes: git diff .github/workflows/")
            print("   • Run local tests: uv run pytest --ignore=Snowfakery")
            print("   • Test scripts directly:")
            print("     - python scripts/version_utils.py validate v0.2.0")
            print("     - python scripts/prepare_release.py --help")
            return 0
        else:
            print("\n❌ Some validation checks failed")
            return 1

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
