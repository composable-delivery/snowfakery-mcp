from __future__ import annotations

import json
from importlib.resources.abc import Traversable
from pathlib import Path


def read_text_utf8(path: Path | Traversable) -> str:
    return path.read_text(encoding="utf-8")


def truncate(text: str, *, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n…(truncated)…\n", True


def smart_truncate_output(
    text: str, *, output_format: str, max_chars: int
) -> tuple[str, bool, int | None]:
    """Truncate captured tool output for a size budget without corrupting it.

    Unlike :func:`truncate`, which slices at a raw character offset, this
    drops only whole trailing units:

    - For ``output_format="json"`` (Snowfakery's JSON output is always a
      flat list of row records), whole trailing *records* are dropped and
      the result is re-serialized, so a truncated result is always valid
      JSON rather than a string cut off mid-object. ``record_count`` is the
      total number of records generated, independent of how many made it
      into the returned text.
    - For every other format, whole trailing *lines* are dropped, so a
      truncated result is never garbage mid-line (though for formats like
      ``sql``/``dot`` it isn't guaranteed to still be fully valid on its
      own). ``record_count`` is ``None`` — there's no well-defined "record"
      for these formats.

    Always keeps at least one unit even if it alone exceeds ``max_chars``,
    so the result is never truncated down to nothing.
    """

    if output_format == "json":
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            total = len(parsed)
            if len(text) <= max_chars:
                return text, False, total
            budget = max(max_chars - 2, 0)  # reserve room for surrounding [ ]
            kept: list[str] = []
            running_len = 0
            for record in parsed:
                part = json.dumps(record)
                added = len(part) + (2 if kept else 0)  # ", " separator
                if running_len + added > budget and kept:
                    break
                kept.append(part)
                running_len += added
            return "[" + ", ".join(kept) + "]", len(kept) < total, total
        # Not a JSON array (unexpected for Snowfakery's json output) - fall
        # through to line-safe truncation below rather than crash.

    if len(text) <= max_chars:
        return text, False, None
    head = text[:max_chars]
    last_newline = head.rfind("\n")
    if last_newline > 0:
        head = head[:last_newline]
    return head + "\n…(truncated)…\n", True, None


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
