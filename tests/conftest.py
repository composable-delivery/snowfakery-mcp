from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    # Convenience flag: users sometimes try `pytest --coverage`.
    # pytest-cov uses `--cov`, so we alias `--coverage` to a basic --cov setup.
    parser.addoption(
        "--coverage",
        action="store_true",
        default=False,
        help="Alias for enabling pytest-cov with a sensible default (--cov=.).",
    )


def pytest_configure(config: pytest.Config) -> None:
    if not getattr(config.option, "coverage", False):
        return

    # Only do anything if pytest-cov is installed.
    if not config.pluginmanager.hasplugin("pytest_cov"):
        raise pytest.UsageError(
            "--coverage requires pytest-cov. Install dev deps or run `uv sync --group dev`."
        )

    # pytest-cov registers these options; set defaults if user didn't specify.
    if not getattr(config.option, "cov_source", None):
        config.option.cov_source = [str(Path.cwd())]

    if not getattr(config.option, "cov_report", None):
        config.option.cov_report = ["term-missing"]
