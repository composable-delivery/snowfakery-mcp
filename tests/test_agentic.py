from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client, Context
from fastmcp.resources import ResourceResult
from fastmcp.server.sampling import SamplingResult
from fastmcp.tools import ToolResult

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.server import mcp as server_app
from snowfakery_mcp.tools.agentic import _iterative_recipe_gen_impl


def _sampling_result(text: str) -> SamplingResult[str]:
    """Build a real SamplingResult, matching Context.sample()'s actual contract."""
    return SamplingResult(text=text, result=text, history=[])


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock(spec=Context)
    # Context.read_resource() returns a ResourceResult (list[ResourceContent]-style
    # .contents), never a bare string - use the real type here so this fixture can't
    # mask a regression the way the old string-based mock did.
    ctx.read_resource.return_value = ResourceResult("mock_schema")
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

    mock_ctx.sample.return_value = _sampling_result("- object: Account\n  fields:\n    name: Test")

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
        _sampling_result("Invalid YAML"),
        _sampling_result("- object: Account"),
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
async def test_iterative_recipe_gen_retry_success_with_real_tool_result_shape(
    mock_ctx, mock_paths, mock_config
):
    """validate_recipe_logic() (the real, unmocked function) returns a plain
    ValidateResult dict on success but a ToolResult(is_error=True) on failure
    (Phase 3's ToolResult(is_error=...) contract) — mock at that same fidelity
    here to cover agentic.py's normalization of both possible shapes, since the
    end-to-end real-client test always succeeds on the first sampling call and
    never exercises the ToolResult(is_error=True) branch."""

    mock_ctx.sample.side_effect = [
        _sampling_result("Invalid YAML"),
        _sampling_result("- object: Account"),
    ]

    with patch("snowfakery_mcp.tools.agentic.validate_recipe_logic") as mock_validate:
        mock_validate.side_effect = [
            ToolResult(
                structured_content={
                    "valid": False,
                    "errors": [{"kind": "SyntaxError", "message": "Bad syntax", "line": 1}],
                },
                is_error=True,
            ),
            {"valid": True, "errors": []},
        ]

        result = await _iterative_recipe_gen_impl(
            goal="Test Goal", max_iterations=3, ctx=mock_ctx, paths=mock_paths, config=mock_config
        )

        assert result == "- object: Account"
        assert mock_ctx.sample.call_count == 2
        # Error feedback extracted from the ToolResult's structured_content, not
        # a stringified repr of the ToolResult object itself.
        args, kwargs = mock_ctx.sample.call_args_list[1]
        messages = kwargs["messages"]
        assert "Bad syntax" in messages[2].content.text
        assert "ToolResult(" not in messages[2].content.text


@pytest.mark.anyio
async def test_iterative_recipe_gen_max_iterations(mock_ctx, mock_paths, mock_config):
    """Test failure after max iterations."""

    mock_ctx.sample.return_value = _sampling_result("Invalid YAML")

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


@pytest.mark.anyio
async def test_iterative_recipe_gen_schema_context_uses_real_text(mock_paths, mock_config):
    """Regression test for the ctx.read_resource() interpolation bug in agentic.py.

    Drives the schema-context fetch with a real ResourceResult and asserts the
    text fed to the LLM is the actual schema content, not a ResourceResult/
    ResourceContent repr.
    """
    ctx = AsyncMock(spec=Context)
    ctx.read_resource.return_value = ResourceResult('{"$schema": "mock"}')
    ctx.sample.return_value = _sampling_result("- object: Account")

    with patch("snowfakery_mcp.tools.agentic.validate_recipe_logic") as mock_validate:
        mock_validate.return_value = {"valid": True, "errors": []}

        await _iterative_recipe_gen_impl(
            goal="Test Goal", max_iterations=1, ctx=ctx, paths=mock_paths, config=mock_config
        )

    _args, kwargs = ctx.sample.call_args
    messages = kwargs["messages"]
    schema_text = messages[0].content.text
    assert '{"$schema": "mock"}' in schema_text
    assert "ResourceContent(" not in schema_text
    assert "ResourceResult(" not in schema_text


def _tool_result_text(result: Any) -> str:
    """Extract text content from a FastMCP CallToolResult."""
    data = result.data
    if isinstance(data, str):
        return data
    return str(data)


@pytest.mark.anyio
async def test_iterative_recipe_gen_real_client_end_to_end() -> None:
    """Drive the real, decorator-registered iterative_recipe_gen tool over the
    in-memory transport using fastmcp.Client(..., sampling_handler=...).

    Regression test for the ctx.sample() result-parsing bug: asserts the
    returned text is the sampling handler's YAML, not a SamplingResult/
    CreateMessageResult dataclass repr.
    """
    expected_recipe = "- object: Account\n  fields:\n    Name: Test"

    async def fake_sampling_handler(messages, params, context):
        return expected_recipe

    client: Client[Any] = Client(server_app, sampling_handler=fake_sampling_handler)
    async with client:
        result = await client.call_tool("iterative_recipe_gen", {"goal": "Generate Accounts"})

    text = _tool_result_text(result)
    assert text == expected_recipe
    assert "SamplingResult(" not in text
    assert "CreateMessageResult(" not in text
