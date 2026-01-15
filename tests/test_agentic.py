from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context
from mcp.types import CreateMessageResult, TextContent

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.tools.agentic import _iterative_recipe_gen_impl


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock(spec=Context)
    ctx.read_resource.return_value = "mock_schema"
    return ctx


@pytest.fixture
def mock_paths():
    return MagicMock(spec=WorkspacePaths)


@pytest.fixture
def mock_config():
    return MagicMock(spec=Config)


@pytest.mark.anyio
async def test_iterative_recipe_gen_success_first_try(mock_ctx, mock_paths, mock_config):
    """Test successful recipe generation on the first attempt."""

    mock_ctx.sample.return_value = CreateMessageResult(
        role="assistant",
        content=TextContent(type="text", text="- object: Account\n  fields:\n    name: Test"),
        model="gpt-4o",
    )

    with patch("snowfakery_mcp.tools.agentic.validate_recipe_logic") as mock_validate:
        mock_validate.return_value = {"valid": True, "errors": []}

        result = await _iterative_recipe_gen_impl(
            goal="Test Goal", max_iterations=3, ctx=mock_ctx, paths=mock_paths, config=mock_config
        )

        assert result == "- object: Account\n  fields:\n    name: Test"
        mock_ctx.sample.assert_called_once()
        mock_validate.assert_called_once()


@pytest.mark.anyio
async def test_iterative_recipe_gen_no_context(mock_paths, mock_config):
    """Test error when no context is provided."""
    result = await _iterative_recipe_gen_impl(
        goal="Test Goal", max_iterations=3, ctx=None, paths=mock_paths, config=mock_config
    )
    assert result == "Error: Context is required for this tool to function."


@pytest.mark.anyio
async def test_iterative_recipe_gen_retry_success(mock_ctx, mock_paths, mock_config):
    """Test successful recipe generation after one failure."""

    # First response: Invalid YAML
    # Second response: Valid YAML
    mock_ctx.sample.side_effect = [
        CreateMessageResult(
            role="assistant", content=TextContent(type="text", text="Invalid YAML"), model="gpt-4o"
        ),
        CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="- object: Account"),
            model="gpt-4o",
        ),
    ]

    with patch("snowfakery_mcp.tools.agentic.validate_recipe_logic") as mock_validate:
        mock_validate.side_effect = [
            {
                "valid": False,
                "errors": [{"kind": "SyntaxError", "message": "Bad syntax", "line": 1}],
            },
            {"valid": True, "errors": []},
        ]

        result = await _iterative_recipe_gen_impl(
            goal="Test Goal", max_iterations=3, ctx=mock_ctx, paths=mock_paths, config=mock_config
        )

        assert result == "- object: Account"
        assert mock_ctx.sample.call_count == 2
        # Check that error feedback was sent
        args, kwargs = mock_ctx.sample.call_args_list[1]
        messages = kwargs["messages"]
        assert len(messages) == 3  # User goal, Assistant invalid, User error feedback
        assert "The recipe is invalid" in messages[2].content.text


@pytest.mark.anyio
async def test_iterative_recipe_gen_max_iterations(mock_ctx, mock_paths, mock_config):
    """Test failure after max iterations."""

    mock_ctx.sample.return_value = CreateMessageResult(
        role="assistant", content=TextContent(type="text", text="Invalid YAML"), model="gpt-4o"
    )

    with patch("snowfakery_mcp.tools.agentic.validate_recipe_logic") as mock_validate:
        mock_validate.return_value = {
            "valid": False,
            "errors": [{"kind": "Error", "message": "Bad", "line": 1}],
        }

        result = await _iterative_recipe_gen_impl(
            goal="Test Goal", max_iterations=2, ctx=mock_ctx, paths=mock_paths, config=mock_config
        )

        assert "Failed to generate valid recipe after 2 attempts" in result
        assert mock_ctx.sample.call_count == 2
