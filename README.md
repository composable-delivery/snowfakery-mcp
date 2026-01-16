# Snowfakery MCP Server

[![CI](https://github.com/composable-delivery/snowfakery-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/composable-delivery/snowfakery-mcp/actions/workflows/ci.yml)
[![Release](https://github.com/composable-delivery/snowfakery-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/composable-delivery/snowfakery-mcp/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/snowfakery-mcp.svg)](https://pypi.org/project/snowfakery-mcp/)
[![Codecov](https://codecov.io/gh/composable-delivery/snowfakery-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/composable-delivery/snowfakery-mcp)
[![License](https://img.shields.io/github/license/composable-delivery/snowfakery-mcp.svg)](LICENSE-MIT)

**Power up your AI workflows with Snowfakery data generation** — Use Claude, ChatGPT, and other AI assistants to author, debug, and run data recipes through the [Model Context Protocol](https://modelcontextprotocol.io/).

## MCP Registry

mcp-name: io.github.composable-delivery/snowfakery-mcp

## What is this?

[Snowfakery](https://github.com/SFDO-Tooling/Snowfakery) is a YAML-based tool for programmatically generating test data. This MCP server connects Snowfakery to AI assistants, letting you:

- **Draft recipes** with AI assistance backed by real Snowfakery docs and examples
- **Validate recipes** before running them with detailed error feedback
- **Execute recipes** and iterate on results interactively
- **Debug issues** with static analysis and recipe inspection
- **Generate Salesforce mappings** for CumulusCI workflows

Perfect for teams that need realistic test data—from Salesforce admins to developers building data pipelines.

## Quick Start

### Install `uv`

We recommend using `uv` for installs and for running from source.

- Install `uv` (macOS/Linux):

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- Install `uv` (Windows PowerShell):

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

See the official `uv` install docs: <https://docs.astral.sh/uv/getting-started/installation/>

### Claude Desktop (recommended)

For Claude Desktop, prefer using the `.mcpb` bundle from Releases:

- Download the latest `.mcpb` from <https://github.com/composable-delivery/snowfakery-mcp/releases>
- Add the bundle in Claude Desktop as an MCP server bundle

This bundle includes the pinned runtime metadata (`uv.lock`, `manifest.json`) and is the easiest way to get a reproducible setup.

### Install & Run (CLI)

```bash
# Recommended: isolated install
uv tool install snowfakery-mcp

# Then run the server
snowfakery-mcp
```

Or from source:

```bash
git clone https://github.com/composable-delivery/snowfakery-mcp.git
cd snowfakery-mcp
uv sync
uv run snowfakery-mcp
```

### Connect to Claude (Desktop)

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "snowfakery-mcp": {
      "command": "snowfakery-mcp"
    }
  }
}
```

Then ask Claude:
> "Show me an example Snowfakery recipe" or "Help me write a recipe to generate 100 Salesforce accounts"

## Features

**Resources** — Access docs, examples, and schemas:

- Snowfakery documentation and recipe examples
- JSON schema for recipe validation
- Run outputs and artifacts

**Tools** — Interact with recipes:

- Validate & analyze recipes (catch errors early)
- Run recipes and capture output
- List & retrieve example recipes
- Generate CumulusCI mapping files

## Learn More

- **[MCP_SERVER_SPEC.md](MCP_SERVER_SPEC.md)** — detailed design and tool catalog
- **[Snowfakery docs](https://snowfakery.readthedocs.io/)** — recipe language reference
- **[Contributing](CONTRIBUTING.md)** — how to contribute

## Community

We want this to be welcoming at any level. Questions, ideas, and contributions are always welcome!

- **Questions & ideas?** Open a [GitHub Discussion](https://github.com/composable-delivery/snowfakery-mcp/discussions)
- **Found a bug?** [Open an Issue](https://github.com/composable-delivery/snowfakery-mcp/issues) with a minimal recipe
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security concern?** See [SECURITY.md](SECURITY.md)

## Development

```bash
# Install dev dependencies
uv sync --all-groups

# Run tests
uv run pytest

# Type check
uv run mypy snowfakery_mcp

# Lint & format
uv run ruff check snowfakery_mcp tests scripts evals
uv run ruff format snowfakery_mcp tests scripts evals
```

### Evals (Agentic Testing)

This repo includes `inspect-ai` tasks for testing the MCP server with AI models:

```bash
# Install eval dependencies
uv sync --group evals

# Run evaluation
uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-4o-mini
```

See [evals/](evals/) for more examples and troubleshooting.

## Notes

- The repo includes the upstream Snowfakery repo as a git submodule (`Snowfakery/`) for development
- When running from source, use `uv run ...` to ensure the pinned environment
- PyPI installs use bundled docs/examples (no submodule required)

## Releases

See [GitHub Releases](https://github.com/composable-delivery/snowfakery-mcp/releases) for sdist, wheel, and `.mcpb` bundles (recommended for Claude Desktop).
