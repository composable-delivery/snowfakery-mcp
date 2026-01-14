# Contributing

Thanks for your interest in contributing!

## Quick start (Codespaces / local)

- Install `uv` (https://docs.astral.sh/uv/)
- `uv sync --all-groups`
- Run tests: `uv run pytest`
- Run typecheck: `uv run mypy snowfakery_mcp`
- Run the MCP server: `uv run snowfakery-mcp`

## Development notes

- This repo vendors Snowfakery as a git submodule in `Snowfakery/` for development-time access to docs, examples, and schema.
- The published package should still function without the submodule present.

## Filing issues

Please use the issue forms. Include:

- What you expected vs what happened
- Repro steps (recipe text or a minimal snippet)
- OS and Python version
- Whether you’re running from a release (`pipx install ...`) or from source (`uv run ...`)

## Pull requests

- Keep changes focused and well tested.
- Add/adjust tests when changing behavior.
- Avoid large refactors unless discussed first.

## License

By contributing, you agree that your contributions will be licensed under the project’s dual license (Apache-2.0 OR MIT).
