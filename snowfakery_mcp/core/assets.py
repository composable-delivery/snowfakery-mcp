from __future__ import annotations

from collections.abc import Iterable
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath

from snowfakery_mcp.core.paths import WorkspacePaths


def docs_root(paths: WorkspacePaths) -> Path | Traversable:
    """Resolve the root directory for Snowfakery docs.

    Prefer the vendored git submodule (dev workflows), but fall back to bundled
    docs shipped inside this package for wheel installs.
    """

    submodule_dir = paths.root / "Snowfakery" / "docs"
    if submodule_dir.exists():
        return submodule_dir
    return resources.files("snowfakery_mcp.bundled_docs")


def examples_root(paths: WorkspacePaths) -> Path | Traversable:
    """Resolve the root directory for Snowfakery example recipes.

    Prefer the vendored git submodule (dev workflows), but fall back to bundled
    examples shipped inside this package for wheel installs.
    """

    submodule_dir = paths.root / "Snowfakery" / "examples"
    if submodule_dir.exists():
        return submodule_dir
    return resources.files("snowfakery_mcp.bundled_examples")


def safe_relpath(name: str) -> PurePosixPath:
    """Validate user-provided resource paths.

    This prevents path traversal (e.g. "../../etc/passwd") when serving bundled
    resources that do not go through WorkspacePaths.ensure_within(...).
    """

    rel = PurePosixPath(name)
    if rel.is_absolute() or rel.drive:
        raise ValueError("name must be a relative path")
    if any(part in {"..", ""} for part in rel.parts):
        raise ValueError("name must not contain '..' or empty segments")
    return rel


def iter_files(root: Path | Traversable, *, suffixes: Iterable[str]) -> list[str]:
    """Return POSIX-style relative file paths under root matching suffixes."""

    suffixes_tuple = tuple(suffixes)
    if isinstance(root, Path):
        matches = [
            str(p.relative_to(root)).replace("\\", "/")
            for p in root.rglob("*")
            if p.is_file() and p.name.endswith(suffixes_tuple)
        ]
        return sorted(matches)

    out: list[str] = []

    def walk(dir_node: Traversable, prefix: str) -> None:
        for child in dir_node.iterdir():
            child_name = child.name
            rel = f"{prefix}{child_name}" if prefix else child_name
            if child.is_dir():
                walk(child, rel + "/")
            else:
                if child_name.endswith(suffixes_tuple):
                    out.append(rel)

    walk(root, "")
    return sorted(out)
