"""Compatibility entrypoint.

Prefer running the server via the console script:

    uv run snowfakery-mcp
"""

from snowfakery_mcp.server import run

if __name__ == "__main__":
    run()
