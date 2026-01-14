from __future__ import annotations

from importlib.resources.abc import Traversable
from pathlib import Path


def read_text_utf8(path: Path | Traversable) -> str:
    return path.read_text(encoding="utf-8")


def truncate(text: str, *, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n…(truncated)…\n", True


def recipe_text_from_input(
    *,
    recipe_path: str | None,
    recipe_text: str | None,
    workspace_root: Path,
) -> str:
    if bool(recipe_path) == bool(recipe_text):
        raise ValueError("Provide exactly one of recipe_path or recipe_text")

    if recipe_text is not None:
        return recipe_text

    assert recipe_path is not None
    path = (
        (workspace_root / recipe_path) if not Path(recipe_path).is_absolute() else Path(recipe_path)
    )
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(workspace_root)
    except Exception as e:
        raise ValueError(f"Path is outside workspace root: {resolved}") from e

    return read_text_utf8(resolved)
