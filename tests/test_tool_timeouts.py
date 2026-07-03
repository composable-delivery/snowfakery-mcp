"""Tests for Phase 5's ``@mcp.tool(timeout=...)`` migration.

Replaces the deleted ``tests/test_core_timeout.py`` (SIGALRM-specific tests
for the now-deleted ``core/timeout.time_limit()``/``OperationTimeout``).

Two things are verified here, deliberately kept separate:

1. **Wiring**: all four tools Phase 5 targets (``run_recipe``,
   ``generate_mapping``, ``validate_recipe``, ``iterative_recipe_gen``)
   actually carry the configured ``timeout=timeout_seconds`` on their
   registered ``fastmcp.tools.Tool`` (i.e. ``register_run_tool`` et al.
   correctly pass it to ``@mcp.tool(...)``).

2. **Genuine enforcement**: ``iterative_recipe_gen`` (the one tool of the
   four that is ``async def`` and therefore actually preemptible by
   ``anyio.fail_after`` -- see its docstring in ``tools/agentic.py``) really
   does surface a timeout failure when a slow sampling round-trip blows
   past its configured deadline, within a bounded, deterministic window.

We deliberately do *not* assert that a monkeypatched, sleeping
``generate_data()`` call causes ``run_recipe``/``generate_mapping``/
``validate_recipe`` to time out: verified directly against the installed
fastmcp 3.4.2, it does not (see ``tools/run.py``'s docstring and
``RELEASE.md``'s Phase 5 entry for the full explanation -- FastMCP's
threadpool dispatch uses ``anyio.to_thread.run_sync(abandon_on_cancel=False)``,
which suppresses cancellation delivery for the entire duration of a
synchronous, thread-dispatched call). Asserting a timeout error there would
assert something false.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import anyio
import pytest
from fastmcp import Client, FastMCP

from conftest import lifespan_stub
from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.tools.agentic import register_agentic_tools
from snowfakery_mcp.tools.mapping import register_mapping_tool
from snowfakery_mcp.tools.run import register_run_tool
from snowfakery_mcp.tools.validate import register_validate_tool

_CUSTOM_TIMEOUT = 7


@pytest.mark.anyio
async def test_all_four_execution_tools_carry_configured_timeout() -> None:
    """``register_run_tool``/``register_mapping_tool``/``register_validate_tool``/
    ``register_agentic_tools`` must each pass their ``timeout_seconds`` argument
    straight through to ``@mcp.tool(timeout=...)``, not silently drop it."""

    app = FastMCP("test", lifespan=lifespan_stub(paths=MagicMock(spec=WorkspacePaths)))
    register_run_tool(app, timeout_seconds=_CUSTOM_TIMEOUT)
    register_mapping_tool(app, timeout_seconds=_CUSTOM_TIMEOUT)
    register_validate_tool(app, timeout_seconds=_CUSTOM_TIMEOUT)
    register_agentic_tools(app, timeout_seconds=_CUSTOM_TIMEOUT)

    for name in ("run_recipe", "generate_mapping", "validate_recipe", "iterative_recipe_gen"):
        tool = await app.get_tool(name)
        assert tool.timeout == _CUSTOM_TIMEOUT, f"{name} did not receive timeout={_CUSTOM_TIMEOUT}"


@pytest.mark.anyio
async def test_iterative_recipe_gen_surfaces_timeout_error_within_bounded_window() -> None:
    """A slow/unresponsive sampling round-trip that blows past
    ``iterative_recipe_gen``'s configured ``timeout=`` must surface as a
    protocol-level error (``CallToolResult.isError``), not hang indefinitely
    or silently return the eventual (late) sampling result as if it had
    succeeded.

    Deliberately short values throughout (1s timeout, ~1.5s handler sleep) to
    stay fast and deterministic -- this is the one call path of the four
    Phase 5 covers where ``timeout=`` is genuinely preemptive (see
    ``tools/agentic.py``'s docstring), so it doesn't need a real
    multi-second sleep to demonstrate the mechanism working.
    """

    app = FastMCP(
        "test",
        lifespan=lifespan_stub(
            paths=MagicMock(spec=WorkspacePaths),
            config=Config(
                timeout_seconds=1,
                max_capture_chars=20000,
                preview_chars=2000,
                max_reps=10,
                max_target_count=1000,
            ),
        ),
    )
    register_agentic_tools(app, timeout_seconds=1)

    async def slow_sampling_handler(messages: Any, params: Any, context: Any) -> str:
        await anyio.sleep(1.5)
        return "- object: Account"  # pragma: no cover - never reached in time

    client: Client[Any] = Client(app, sampling_handler=slow_sampling_handler)
    async with client:
        t0 = time.monotonic()
        result = await client.call_tool(
            "iterative_recipe_gen",
            {"goal": "Generate Accounts"},
            raise_on_error=False,
        )
        elapsed = time.monotonic() - t0

    assert result.is_error is True
    text = str(result.content[0].text) if result.content else ""
    assert "timed out" in text.lower()
    # Bounded: the client's own single-threaded read loop doesn't get back to
    # processing the server's early error response until the (short) slow
    # handler finishes, so this isn't as tight as the 1s deadline itself, but
    # it must never approach anything resembling a hang.
    assert elapsed < 5.0
