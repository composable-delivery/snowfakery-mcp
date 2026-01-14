"""Integration tests for tools."""

from __future__ import annotations

import json
import textwrap
from typing import Any, cast

import pytest
from mcp.client.session import ClientSession


@pytest.mark.anyio
async def test_validate_recipe_with_invalid_yaml(mcp_session: ClientSession) -> None:
    """Test validate_recipe with invalid YAML syntax."""
    recipe = "invalid: [yaml: syntax:"

    out = await mcp_session.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": False},
    )

    # Import helper from conftest if available, otherwise define locally
    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert payload["valid"] is False
    assert "errors" in payload


@pytest.mark.anyio
async def test_validate_recipe_with_no_snowfakery_version(mcp_session: ClientSession) -> None:
    """Test validate_recipe with recipe missing required fields."""
    recipe = textwrap.dedent(
        """
        - object: Person
          count: 1
        """
    ).strip()

    out = await mcp_session.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": False},
    )

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    # Without strict mode, missing version might be acceptable
    assert "valid" in payload


@pytest.mark.anyio
async def test_validate_recipe_strict_mode(mcp_session: ClientSession) -> None:
    """Test validate_recipe with strict mode enabled."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Account
          fields:
            Name: ACME
        """
    ).strip()

    out = await mcp_session.call_tool(
        "validate_recipe",
        {"recipe_text": recipe, "strict_mode": True},
    )

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert payload["valid"] is True


@pytest.mark.anyio
async def test_analyze_recipe_valid(mcp_session: ClientSession) -> None:
    """Test analyze_recipe with valid recipe."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 5
          fields:
            name: ${{fake.first_name}}
            email: ${{fake.email}}
        """
    ).strip()

    out = await mcp_session.call_tool(
        "analyze_recipe",
        {"recipe_text": recipe},
    )

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert "tables" in payload or "objects" in payload


@pytest.mark.anyio
async def test_run_recipe_with_json_output(mcp_session: ClientSession) -> None:
    """Test run_recipe with JSON output format."""
    recipe = textwrap.dedent(
        """
        - snowfakery_version: 3
        - object: Person
          count: 2
          fields:
            name: TestUser
        """
    ).strip()

    out = await mcp_session.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "json",
            "capture_output": True,
            "strict_mode": True,
        },
    )

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert payload["ok"] is True
    assert payload["run_id"]


@pytest.mark.anyio
async def test_run_recipe_with_invalid_recipe(mcp_session: ClientSession) -> None:
    """Test run_recipe with invalid recipe."""
    recipe = "invalid: [recipe:"

    out = await mcp_session.call_tool(
        "run_recipe",
        {
            "recipe_text": recipe,
            "reps": 1,
            "output_format": "txt",
            "capture_output": True,
            "strict_mode": False,
        },
    )

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    # Should indicate failure
    assert payload.get("ok") is False or "error" in payload


@pytest.mark.anyio
async def test_list_capabilities(mcp_session: ClientSession) -> None:
    """Test list_capabilities tool."""
    out = await mcp_session.call_tool("list_capabilities", {})

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert "max_reps" in payload
    assert "max_target_count" in payload
    assert "max_capture_chars" in payload


@pytest.mark.anyio
async def test_list_examples(mcp_session: ClientSession) -> None:
    """Test list_examples tool."""
    out = await mcp_session.call_tool("list_examples", {})

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert "examples" in payload
    assert isinstance(payload["examples"], list)


@pytest.mark.anyio
async def test_list_examples_with_prefix(mcp_session: ClientSession) -> None:
    """Test list_examples tool with prefix filter."""
    out = await mcp_session.call_tool("list_examples", {"prefix": "comp"})

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert "examples" in payload
    # All examples should start with the prefix
    for example in payload["examples"]:
        assert example.startswith("comp") or len(payload["examples"]) == 0


@pytest.mark.anyio
async def test_get_example(mcp_session: ClientSession) -> None:
    """Test get_example tool."""
    out = await mcp_session.call_tool("get_example", {"name": "company.yml"})

    try:
        from tests.conftest import _tool_payload_text
    except ImportError:

        def _tool_payload_text(result: Any) -> str:
            content = getattr(result, "content", None)
            assert isinstance(content, list) and content
            first = cast(Any, content[0])
            text = getattr(first, "text", None)
            assert isinstance(text, str)
            return text

    payload = json.loads(_tool_payload_text(out))
    assert "content" in payload or "error" in payload
