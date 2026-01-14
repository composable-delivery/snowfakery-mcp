This repository provides the MCP (Model Context Protocol) server for Snowfakery — a tool to author, validate, analyze, and run Snowfakery recipes programmatically.

Quick links

- **Docs:** https://snowfakery.readthedocs.io/
- **Upstream repo:** https://github.com/SFDO-Tooling/Snowfakery

Getting started

- Install from PyPI (recommended, isolated): `pipx install snowfakery-mcp`
- Run installed binary: `snowfakery-mcp`
- Run from source (development):
	- `uv sync --all-groups`
	- `uv run snowfakery-mcp`

Development

- Install dev deps: `uv sync --all-groups`
- Tests: `uv run pytest`
- Typecheck: `uv run mypy snowfakery_mcp`
- Lint: `uv run ruff check snowfakery_mcp tests scripts evals`
- Format: `uv run ruff format snowfakery_mcp tests scripts evals`

Notes

- The repository vendors the upstream Snowfakery repo as a git submodule under `Snowfakery/` to access the canonical docs and examples while developing. When the submodule is not present (for example, in a PyPI install), the package falls back to a bundled snapshot of docs/examples.
- For Snowfakery-related commands locally prefer `uv run ...` to ensure the pinned environment is used.

What's included (MVP)

- Resources: schema, docs, example recipes and run artifacts exposed as `snowfakery://...` MCP resources.
- Tools: recipe validation, static analysis, run execution, example listing, schema retrieval, and mapping generation.

Evals (inspect-ai)

This repo includes an `inspect-ai` task that exercises the MCP tools for agentic evaluation. See `evals/` for examples and use `uv run inspect` helpers to run and view logs.

Community & contribution

We want this project to be welcoming and easy to engage with at any level. A few notes on where to ask questions and how we triage work:

- **Discussions (recommended):** enable GitHub Discussions for general questions, how-tos, design conversations, and proposals. Use Discussions for:
	- Asking how to model a dataset or recipe pattern
	- Proposing new features or UX changes
	- Roadmap conversations and community proposals
	- Sharing examples and integrations

- **Issues (bugs & feature requests):** use Issues for reproducible bugs and scoped feature requests. When filing an issue include:
	- What you expected vs what happened
	- Minimal repro steps (recipe text or snippet)
	- OS / Python version and whether you ran from a release or from source

- **Conversion flow:** maintainers may convert a Discussion to an Issue (or link an Issue) when work is ready to be tracked. Issues that are accepted for work are added to the project board and assigned labels and milestones.

- **Projects & tasks:** we use GitHub Projects (or the chosen project tool) to track work. The typical flow:
	1. Discussion or Issue is created
	2. Maintainers triage and label the Issue
	3. If accepted, Issue is added to the project board and given an owner/estimate
	4. Work is done in a feature branch and linked back to the Issue/Project

- **Pull requests:** keep PRs focused and small. Add tests for behavior changes and reference the related Issue. Expect review from one or more maintainers before merge.

- **Code of Conduct & Security:** see `CODE_OF_CONDUCT.md` and `SECURITY.md` for reporting guidance. For suspected security vulnerabilities, use GitHub Security Advisories rather than a public issue.

Where to get help quickly

- Open a new discussion (Questions category) for quick usage help.
- If you’re running into a bug that reproduces reliably, open an Issue and attach a minimal recipe.

Releases

We ship sdist and wheel artifacts and occasionally an experimental `.mcpb` bundle containing metadata and sample configs. See the Releases page on GitHub for assets and notes.

Files to review

- [MCP_SERVER_SPEC.md](MCP_SERVER_SPEC.md) — server design and tool catalog
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and triage guidance
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards
- [SECURITY.md](SECURITY.md) — vulnerability reporting

If you'd like, I can open PRs to add Discussion templates and Issue forms, or create a small `community/` doc directory with examples for triage labels and templates.


# snowfakery-mcp

MCP server for authoring, analyzing, debugging, and running Snowfakery recipes.

Upstream Snowfakery:

- Repo: https://github.com/SFDO-Tooling/Snowfakery
- Docs: https://snowfakery.readthedocs.io/


See [MCP_SERVER_SPEC.md](MCP_SERVER_SPEC.md) for the initial server spec.

## Run the server

Install dependencies and run the MCP server over stdio:

- `uv sync`
- `uv run snowfakery-mcp`

Install from releases / PyPI:

- Recommended (isolated): `pipx install snowfakery-mcp`
- Or: `python -m pip install snowfakery-mcp`
- Then run: `snowfakery-mcp`

## Development

- Install all groups (dev + evals): `uv sync --all-groups`
- Run tests: `uv run pytest`
- Typecheck: `uv run mypy snowfakery_mcp`
- Lint: `uv run ruff check snowfakery_mcp tests scripts evals`
- Format: `uv run ruff format snowfakery_mcp tests scripts evals`

Notes:

- The repo includes the upstream Snowfakery repo as a git submodule under `Snowfakery/`.
- The MCP server serves `snowfakery://docs/*` and `snowfakery://examples/*` from the submodule when present, but falls back to a bundled snapshot shipped inside the `snowfakery_mcp` wheel for installs where submodules are not available.
- When running any Snowfakery-related commands locally, prefer `uv run ...` to ensure you’re using the pinned environment.

## What’s included (MVP)

- Resources:
	- `snowfakery://schema/recipe-jsonschema`
	- `snowfakery://docs/index` / `snowfakery://docs/extending` / `snowfakery://docs/salesforce` / `snowfakery://docs/architecture`
	- `snowfakery://examples/list` and `snowfakery://examples/{name}`
	- `snowfakery://runs/{run_id}/{artifact}` for run artifacts
- Tools:
	- `list_capabilities`, `list_examples`, `get_example`, `get_schema`, `search_docs`
	- `validate_recipe`, `analyze_recipe`, `run_recipe`, `generate_mapping`

## Evals (inspect-ai)

For more agentic evals (tool use + iterative debugging), this repo includes an `inspect-ai` task that exposes the full MCP tool suite to the model.

- Install eval deps:
	- `uv sync --group evals`
- Run:
	- `uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model <api>/<model_name>`
	- (Optional) set a base URL with `INSPECT_EVAL_MODEL_BASE_URL` or `--model-base-url`.

Examples:

- `uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-4o-mini`
- `OPENAI_API_KEY=$GITHUB_TOKEN INSPECT_EVAL_MODEL_BASE_URL=https://models.inference.ai.azure.com uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-4o-mini`

GitHub Models notes:

- Some GitHub Models endpoints do not support the OpenAI `responses` API yet. If you see `api_not_supported` or a 404 to `/responses`, force chat-completions mode:
	- `OPENAI_API_KEY=$GITHUB_TOKEN INSPECT_EVAL_MODEL_BASE_URL=https://models.inference.ai.azure.com uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-5-mini -M responses_api=false --display plain`

- GitHub Models can also rate-limit aggressively, and a parallel eval can *look* hung while requests are being retried. For the most reliable runs, go serial:
	- `OPENAI_API_KEY=$GITHUB_TOKEN INSPECT_EVAL_MODEL_BASE_URL=https://models.inference.ai.azure.com uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-5-mini -M responses_api=false --display plain --max-samples 1 --max-connections 1`
	- (Optional) add timeouts to fail fast: `--timeout 90 --attempt-timeout 90`

- To run just one sample at a time:
	- `... --sample-id debug_broken_reference`
	- `... --sample-id salesforce_standard_objects`

Troubleshooting:

- If it "hangs" with no visible progress, use `--display plain` (or set `INSPECT_DISPLAY=plain`).
- To narrow down a slow sample: add `--limit 1`.
- If it still looks stuck, check whether the log is growing:
	- `ls -lt logs | head`
	- `uv run inspect log dump logs/<file>.eval --header-only`

View logs:

- List recent runs: `uv run inspect log list`
- Dump a log as JSON: `uv run inspect log dump logs/<file>.eval`
- Convert to JSON log format: `uv run inspect log convert logs/<file>.eval --to json --output-dir logs-json`
- Start the log viewer (web UI): `uv run inspect view start --log-dir logs`

Quick summaries (when JSON is huge):

- Dump a log then summarize it:
	- `uv run inspect log dump logs/<file>.eval > out.json`
	- `uv run python evals/summarize_log.py out.json`

## Releases

GitHub Releases attach:

- Python sdist + wheel in `dist/`
- An experimental `.mcpb` bundle (a ZIP with metadata + example config)

