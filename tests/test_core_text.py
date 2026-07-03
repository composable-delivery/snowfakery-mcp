from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowfakery_mcp.core.text import recipe_text_from_input, smart_truncate_output, truncate


def test_truncate_noop() -> None:
    text, truncated = truncate("abc", max_chars=10)
    assert text == "abc"
    assert truncated is False


def test_truncate_truncates() -> None:
    text, truncated = truncate("abcdefghij", max_chars=3)
    assert text.startswith("abc")
    assert truncated is True


def test_smart_truncate_output_json_no_truncation_needed() -> None:
    records = [{"id": i} for i in range(3)]
    text, truncated, record_count = smart_truncate_output(
        json.dumps(records), output_format="json", max_chars=10_000
    )
    assert truncated is False
    assert record_count == 3
    assert json.loads(text) == records


def test_smart_truncate_output_json_truncates_to_valid_json() -> None:
    records = [{"id": i, "name": f"person-{i}"} for i in range(200)]
    text, truncated, record_count = smart_truncate_output(
        json.dumps(records), output_format="json", max_chars=200
    )
    assert truncated is True
    assert record_count == 200  # total generated, independent of how many are inline
    parsed = json.loads(text)  # must always be valid JSON, never a mid-object cut
    assert isinstance(parsed, list)
    assert 0 < len(parsed) < 200
    assert parsed == records[: len(parsed)]


def test_smart_truncate_output_json_always_keeps_at_least_one_record() -> None:
    records = [{"id": 0, "padding": "x" * 500}]
    text, truncated, record_count = smart_truncate_output(
        json.dumps(records), output_format="json", max_chars=10
    )
    assert truncated is False  # only one record exists and it's kept in full
    assert record_count == 1
    assert json.loads(text) == records


def test_smart_truncate_output_json_falls_back_on_non_array() -> None:
    # Not expected from Snowfakery's own json output, but must not crash.
    text, truncated, record_count = smart_truncate_output(
        "not json at all " * 20, output_format="json", max_chars=20
    )
    assert truncated is True
    assert record_count is None


def test_smart_truncate_output_txt_truncates_at_line_boundary() -> None:
    text = "line one\nline two\nline three\n"
    truncated_text, truncated, record_count = smart_truncate_output(
        text, output_format="txt", max_chars=15
    )
    assert truncated is True
    assert record_count is None
    body = truncated_text.split("\n…(truncated)…\n")[0]
    assert text.startswith(body)
    assert not body.endswith("line tw")  # never cuts mid-line


def test_smart_truncate_output_no_truncation_needed_for_txt() -> None:
    text, truncated, record_count = smart_truncate_output(
        "short", output_format="txt", max_chars=100
    )
    assert text == "short"
    assert truncated is False
    assert record_count is None


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
        recipe_text_from_input(
            recipe_path="x.yml", recipe_text="- object: X", workspace_root=tmp_path
        )
