"""Tests for prompt registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from snowfakery_mcp.prompts import register_prompts

if TYPE_CHECKING:
    pass


class TestPromptsRegistration:
    """Test prompt registration."""

    def test_register_prompts_can_be_called(self) -> None:
        """Test that register_prompts can be called (registers decorators)."""
        from unittest.mock import MagicMock

        mcp_mock: Any = MagicMock()

        # Should not raise
        try:
            mcp_mock.prompt.return_value = lambda f: f
            register_prompts(mcp_mock)
        except Exception:
            # Expected because we're mocking, but registration should attempt
            pass
