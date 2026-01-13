from __future__ import annotations

import sys
from typing import Any

import click
from snowfakery.api import SnowfakeryApplication


class MCPApplication(SnowfakeryApplication):  # type: ignore[misc]
    """Snowfakery application suitable for MCP stdio.

    MCP stdio requires that stdout is reserved for JSON-RPC messages.
    Snowfakery emits user-facing progress messages via `parent_application.echo`.
    This subclass forces those messages to stderr.
    """

    def echo(
        self,
        message: object | None = None,
        file: Any = None,
        nl: bool = True,
        err: bool = False,
        color: bool | None = None,
    ) -> None:
        _ = file
        _ = err
        click.echo(message=message, file=sys.stderr, nl=nl, err=True, color=color)
