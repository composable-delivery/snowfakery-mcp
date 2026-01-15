from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Context

from snowfakery_mcp.prompts import register_prompts


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    # Capture the decorator function
    prompts = {}

    def prompt_decorator(**kwargs):
        def decorator(func):
            prompts[func.__name__] = func
            return func

        return decorator

    mcp.prompt.side_effect = prompt_decorator

    # Register prompts
    register_prompts(mcp)

    # Attach registered prompts to the mock object for easy access
    mcp.registered_prompts = prompts
    return mcp


@pytest.mark.anyio
async def test_author_recipe_schema_failure(mock_mcp):
    """Test author_recipe prompt when schema resource fetch fails."""
    author_recipe = mock_mcp.registered_prompts["author_recipe"]

    # Mock context to raise exception when reading resource
    ctx = AsyncMock(spec=Context)
    ctx.read_resource.side_effect = Exception("Schema load failed")

    result = await author_recipe(goal="My Goal", ctx=ctx)

    assert "Note: Could not load schema automatically" in result
    assert "Goal:\nMy Goal" in result


@pytest.mark.anyio
async def test_debug_recipe(mock_mcp):
    """Test debug_recipe prompt."""
    debug_recipe = mock_mcp.registered_prompts["debug_recipe"]

    # FastMCP prompts can be sync or async. debug_recipe is sync in source.
    result = debug_recipe(recipe_yaml="yaml", error="error")
    assert "Recipe:\nyaml" in result
    assert "Error output:\nerror" in result
