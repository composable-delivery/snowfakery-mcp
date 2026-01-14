# VS Code Development Environment

This repository includes a fully configured VS Code environment with automatic formatting, linting, and type checking.

## Setup

The environment is configured to work with `uv` for Python package management:

```bash
# Install dependencies
uv sync

# Or if using Codespaces, the postCreate.sh will do this automatically
```

## Features

### Automatic on Save

- **Format**: Ruff formatter runs on save
- **Lint**: Ruff linter checks code style
- **Imports**: Ruff organizes imports
- **Type Check**: Pylance provides real-time type checking (strict mode)

### Available Tasks

Open the VS Code Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and search for "Tasks: Run Task":

- **Install dependencies (uv)** — Install all dev dependencies
- **Format with Ruff** — Format entire codebase
- **Lint with Ruff** — Check for linting issues
- **Type check with mypy** — Run mypy on source
- **Check all** — Run format check + lint + type check
- **Run tests** — Run pytest suite
- **Run tests with coverage** — Generate coverage report
- **Run MCP server** — Start the MCP server

### Debug Configurations

The `.vscode/launch.json` includes debug configurations:

- **Python: MCP Server** — Debug the MCP server
- **Python: Pytest** — Debug current test file
- **Python: Pytest (all)** — Debug all tests

To start debugging, press `F5` or click the Debug icon in the sidebar.

### Extensions

Recommended extensions are listed in `.vscode/extensions.json` and will be suggested when you open the workspace.

Key extensions:
- **Python** - Official Python support
- **Pylance** - Advanced type checking and language features
- **Ruff** - Fast Python linter and formatter
- **Debugpy** - Python debugger

### Configuration

The settings are defined in `.vscode/settings.json` and apply to this workspace only:

- **Target Python**: 3.12
- **Line length**: 100 characters
- **Type checking**: Strict mode
- **Formatter**: Ruff
- **Linter**: Ruff with isort integration

## Codespaces

When opening this repo in GitHub Codespaces, the environment is automatically configured via `.devcontainer/devcontainer.json` and the `postCreate.sh` script runs:

```bash
#!/bin/bash
set -e
echo "Installing dependencies with uv..."
uv sync
echo "✓ Ready to develop!"
```

## For Portable Use

The configuration is fully portable and will work:
- ✅ Locally with `uv` installed
- ✅ In Codespaces (auto-configured)
- ✅ In Docker containers with Python 3.12+
- ✅ With any standard VS Code installation

All paths are workspace-relative and configuration uses standard VS Code settings.
