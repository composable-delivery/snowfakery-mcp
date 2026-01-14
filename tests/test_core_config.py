"""Tests for core configuration module."""

from __future__ import annotations

from unittest.mock import patch

from snowfakery_mcp.core.config import Config


class TestConfigFromEnv:
    """Test Config.from_env() with various environment configurations."""

    def test_default_config_values(self) -> None:
        """Test that Config uses sensible defaults when env vars are not set."""
        with patch.dict({}, clear=True):
            config = Config.from_env()
            assert config.max_reps == 10
            assert config.max_target_count == 1000
            assert config.max_capture_chars == 20000
            assert config.timeout_seconds == 30

    def test_custom_config_values(self) -> None:
        """Test that Config reads custom values from environment variables."""
        env = {
            "SNOWFAKERY_MCP_MAX_REPS": "50",
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": "500",
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": "50000",
            "SNOWFAKERY_MCP_TIMEOUT_SECONDS": "60",
        }
        with patch.dict("os.environ", env, clear=False):
            config = Config.from_env()
            assert config.max_reps == 50
            assert config.max_target_count == 500
            assert config.max_capture_chars == 50000
            assert config.timeout_seconds == 60

    def test_invalid_int_env_vars_ignored(self) -> None:
        """Test that invalid integers in env vars are ignored."""
        env = {
            "SNOWFAKERY_MCP_MAX_REPS": "not_a_number",
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": "invalid",
        }
        with patch.dict("os.environ", env, clear=False):
            config = Config.from_env()
            # Should use defaults when invalid values are provided
            assert config.max_reps == 10
            assert config.max_target_count == 1000

    def test_values_below_min_clamped(self) -> None:
        """Test that values below minimum are clamped to min_value."""
        env = {
            "SNOWFAKERY_MCP_MAX_REPS": "0",
        }
        with patch.dict("os.environ", env, clear=False):
            config = Config.from_env()
            # Values below min_value are clamped to min_value (1)
            assert config.max_reps == 1

    def test_values_above_max_clamped(self) -> None:
        """Test that values above maximum are clamped to max_value."""
        env = {
            "SNOWFAKERY_MCP_MAX_REPS": "200000",  # exceeds max of 100_000
        }
        with patch.dict("os.environ", env, clear=False):
            config = Config.from_env()
            # Values above max are clamped to max_value
            assert config.max_reps == 100_000

    def test_timeout_below_min(self) -> None:
        """Test timeout below minimum is clamped to min_value."""
        env = {"SNOWFAKERY_MCP_TIMEOUT_SECONDS": "-1"}
        with patch.dict("os.environ", env, clear=False):
            config = Config.from_env()
            # Clamped to min_value of 1
            assert config.timeout_seconds == 1
