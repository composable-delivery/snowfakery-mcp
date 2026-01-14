# Contributing

Thanks for your interest in contributing to snowfakery-mcp!

## Quick start (Codespaces / local)

- Install `uv` (<https://docs.astral.sh/uv/>)
- `uv sync --all-groups`
- Run tests: `uv run pytest`
- Run typecheck: `uv run mypy snowfakery_mcp`
- Run the MCP server: `uv run snowfakery-mcp`

## Development notes

- This repo vendors Snowfakery as a git submodule in `Snowfakery/` for development-time access to docs, examples, and schema.
- The published package should still function without the submodule present.

## Community process

We welcome contributions at any level — from questions and examples to full features. Here's how we prefer to work so everyone can participate effectively.

1. Discussions: start informal design, usage, or proposal conversations in GitHub Discussions. Use the following categories when available: `Q&A`, `How-to`, `Ideas`, or `Show and tell`.
2. Issues: open an Issue for reproducible bugs or scoped feature requests. If a Discussion leads to actionable work, a maintainer may convert it into an Issue.
3. Projects: accepted Issues are added to the project board and scheduled by maintainers. Work is done in feature branches and linked to the Issue.

### Filing high-quality issues

Include the following to help triage quickly:

- **Expected vs actual behavior** — short description
- **Minimal reproduction** — recipe snippet or steps to reproduce
- **Environment** — OS, Python version, and whether you ran from a release or from source
- **Logs / traceback** — redact secrets

### Pull request guidance

- Keep PRs focused and small. Prefer one change per PR.
- Add or update tests when changing behavior.
- Reference the related Issue in the PR description (eg, "Fixes #123").
- Expect maintainers to request changes; be responsive to feedback.

If you want help drafting a contribution, open a Discussion in the `How-to` or `Ideas` category and tag maintainers.

## Filing issues

Please use the issue forms. Include:

- What you expected vs what happened
- Repro steps (recipe text or a minimal snippet)
- OS and Python version
- Whether you’re running from a release (`pipx install ...`) or from source (`uv run ...`)

## License

By contributing, you agree that your contributions will be licensed under the project’s dual license (Apache-2.0 OR MIT).
