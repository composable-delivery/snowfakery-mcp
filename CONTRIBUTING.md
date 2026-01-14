# Contributing

We welcome contributions at any level! Whether you're asking questions, sharing examples, reporting bugs, or building features, you're making this project better.

## Getting Started

### Setup

We use `uv` for a fast, predictable Python environment:

```bash
# Clone and install
git clone https://github.com/composable-delivery/snowfakery-mcp.git
cd snowfakery-mcp
uv sync --all-groups

# Quick verification
uv run pytest
uv run mypy snowfakery_mcp
```

### Development commands

```bash
# Run the MCP server locally
uv run snowfakery-mcp

# Run tests
uv run pytest

# Type check
uv run mypy snowfakery_mcp

# Lint & format
uv run ruff check snowfakery_mcp tests scripts evals
uv run ruff format snowfakery_mcp tests scripts evals
```

### Important: Git submodule

This repo vendors Snowfakery as a git submodule (`Snowfakery/`). When developing:

```bash
# Initialize submodule (if not present)
git submodule update --init

# Update to latest upstream
git submodule update --remote
```

The published package works without the submodule (falls back to bundled docs/examples), but development benefits from having the full upstream repo for docs and examples.

## How to Contribute

### Questions & Ideas

Start a [GitHub Discussion](https://github.com/composable-delivery/snowfakery-mcp/discussions) if you want to:
- Ask how to use the server or write recipes
- Propose new features or UX improvements
- Discuss design or implementation approaches
- Share examples or integrations

This keeps conversations discoverable and helps maintainers understand what's most valuable to the community.

### Bugs & Feature Requests

[Open an Issue](https://github.com/composable-delivery/snowfakery-mcp/issues) for:
- Reproducible bugs with minimal steps
- Scoped feature requests with clear use cases

**Include in your issue:**
- What you expected vs what actually happened
- Minimal reproduction (recipe snippet or steps)
- Your environment: OS, Python version, and installation method (release vs source)
- Any relevant logs or error messages (redact secrets)

### Code Contributions

Pull requests are always welcome! Keep these guidelines in mind:

**Before starting:**
- Check if an Issue exists for your work. If not, open a Discussion or Issue first.
- For larger changes, discuss your approach before investing a lot of time.

**When submitting a PR:**
- Keep it focused and small. One feature or fix per PR.
- Add tests for any behavior changes.
- Reference the related Issue in the PR description (e.g., "Fixes #123").
- Expect feedback—maintainers will review and may request changes. That's normal and helpful!

**Code standards:**
- Type hints throughout
- Tests for new behavior
- Follow existing code style (use `ruff format` to auto-format)

## Licensing

By contributing, you agree that your contributions are licensed under the project's dual license: Apache-2.0 OR MIT.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). We're committed to a welcoming, harassment-free community.

## Security

Found a security vulnerability? Please don't open a public Issue. Instead, use [GitHub Security Advisories](https://github.com/composable-delivery/snowfakery-mcp/security/advisories) to report it privately. See [SECURITY.md](SECURITY.md) for details.

## Questions?

Open a Discussion or reach out to maintainers. We're here to help!
