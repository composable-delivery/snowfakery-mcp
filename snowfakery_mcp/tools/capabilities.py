from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from snowfakery.__about__ import __version__ as snowfakery_version
from snowfakery.api import file_extensions

from snowfakery_mcp.core.config import Config


def register_capabilities_tools(mcp: FastMCP, config: Config) -> None:
    @mcp.tool(tags={"discovery", "info"})
    def list_capabilities() -> dict[str, Any]:
        """Return Snowfakery + server capability info.

        Use this tool first to understand what the server can do, including:
        - Snowfakery version
        - Supported output formats
        - Server limits (timeout, max output, max reps)
        - Available resources
        """

        return {
            "snowfakery_version": snowfakery_version,
            "supported_output_formats": list(file_extensions),
            "timeout_seconds": config.timeout_seconds,
            "max_capture_chars": config.max_capture_chars,
            "max_reps": config.max_reps,
            "max_target_count": config.max_target_count,
            "limits": {
                "timeout_seconds": config.timeout_seconds,
                "max_capture_chars": config.max_capture_chars,
                "max_reps": config.max_reps,
                "max_target_count": config.max_target_count,
            },
            "resources": {
                "schema": "snowfakery://schema/recipe-jsonschema",
                "docs": [
                    "snowfakery://docs/index",
                    "snowfakery://docs/extending",
                    "snowfakery://docs/salesforce",
                    "snowfakery://docs/architecture",
                ],
                "examples": "snowfakery://examples/list",
            },
        }
