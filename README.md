
# snowfakery-mcp

MCP server for authoring, analyzing, debugging, and running Snowfakery recipes.


See [MCP_SERVER_SPEC.md](MCP_SERVER_SPEC.md) for the initial server spec.

## Run the server

Install dependencies and run the MCP server over stdio:

- `uv sync`
- `uv run snowfakery-mcp`

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

