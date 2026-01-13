from __future__ import annotations

from pathlib import Path

import pytest

from snowfakery_mcp.core.text import recipe_text_from_input, truncate


def test_truncate_noop() -> None:
    text, truncated = truncate("abc", max_chars=10)
    assert text == "abc"
    assert truncated is False


def test_truncate_truncates() -> None:
    text, truncated = truncate("abcdefghij", max_chars=3)
    assert text.startswith("abc")
    assert truncated is True


def test_recipe_text_from_input_path(tmp_path: Path) -> None:
    recipe_path = tmp_path / "r.yml"
    recipe_path.write_text("- snowfakery_version: 3\n", encoding="utf-8")

    # Use workspace_root=tmp_path and pass a relative recipe_path.
    text = recipe_text_from_input(recipe_path="r.yml", recipe_text=None, workspace_root=tmp_path)
    assert "snowfakery_version" in text


def test_recipe_text_from_input_requires_exactly_one(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        recipe_text_from_input(recipe_path=None, recipe_text=None, workspace_root=tmp_path)

    with pytest.raises(ValueError):
        recipe_text_from_input(recipe_path="x.yml", recipe_text="- object: X", workspace_root=tmp_path)
