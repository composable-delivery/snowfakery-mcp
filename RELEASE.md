# Releasing `snowfakery-mcp`

This repo publishes releases via GitHub Actions.

## Breaking changes pending release

Deliberate, wire-visible breaking changes landed on `refactor/fastmcp-3.x` that should be
called out explicitly in the release notes for the tag that ships them:

- **Tool error contract (`ToolResult(is_error=...)`)** — `run_recipe`, `generate_mapping`,
  `validate_recipe`, and `analyze_recipe` now set the protocol-level `CallToolResult.isError`
  flag (via `fastmcp.tools.ToolResult(..., is_error=True)`) whenever they return a failure
  result. Previously `isError` was always `False`, even for `{"ok": False, ...}`/
  `{"valid": False, ...}` payloads, and `analyze_recipe` had no structured error contract at
  all (a malformed recipe surfaced only as a bare `isError=True` text message with no
  `structured_content`). Any client that used `raise_on_error=True` (the FastMCP `Client`
  default) or otherwise branches on `CallToolResult.isError`/`response.isError` will now see
  those calls treated as errors. Clients should inspect the (unchanged) structured payload
  shape — `{"ok": false, "error": {...}}` for `run_recipe`/`generate_mapping`,
  `{"valid": false, "errors": [...]}` for `validate_recipe`, `{"error": {...}}` for
  `analyze_recipe` — the same way they always have; only the `isError` signal is new.
- **`run_recipe`'s output schema no longer wraps results in `{"result": {...}}`** —
  `run_recipe`'s return type is a `Union[RunOkResult, RunErrorResult]`, which FastMCP
  auto-wraps in a synthetic `{"result": {...}}` envelope by default (its advertised
  `outputSchema` and actual `structuredContent` both changed shape as a result). `run_recipe`
  now declares an explicit `output_schema=` that keeps the real per-branch schema without the
  wrap, so `structuredContent` now exposes `ok`/`run_id`/etc. directly at the top level instead
  of nested under a `"result"` key. `generate_mapping`/`validate_recipe` also now declare
  explicit output schemas for consistency, though neither was actually wrapped before this
  change.
- **`analyze_recipe` now advertises no `outputSchema`** — its return type annotation is now
  `dict[str, Any] | ToolResult` (needed for the `is_error=True` change above). FastMCP
  intentionally skips output-schema auto-generation for any tool whose return type includes
  `ToolResult`, since a `ToolResult`'s shape is self-describing at runtime rather than statically
  knowable. Previously `analyze_recipe` advertised a generic, maximally-permissive
  `{"type": "object", "additionalProperties": true}` schema; `structuredContent` itself is
  unaffected (still the same `dict` on success), so this only matters to clients that
  specifically introspected `tools/list`'s `outputSchema` for this tool.

See `FASTMCP3_REFACTOR_PLAN.md` Phase 3 for the full rationale.

- **Timeout errors are now `McpError`-shaped, not the old `OperationTimeout`/`ToolResult` dict** —
  `run_recipe`, `generate_mapping`, `validate_recipe`, and `iterative_recipe_gen` now declare
  `@mcp.tool(timeout=...)` (FastMCP's built-in per-call deadline) instead of wrapping their work
  in the old SIGALRM-based `time_limit()`, which is deleted. When a tool exceeds its configured
  timeout, FastMCP raises the failure at the protocol level (`CallToolResult.isError = True` with
  a generic `"Tool '<name>' execution timed out after <n>s"` text message) rather than returning
  the old `ToolResult(structured_content={"ok": False, "error": {"kind": "OperationTimeout", ...}},
  is_error=True)` shape. Clients that pattern-matched on `error.kind == "OperationTimeout"` need
  updating. Honest caveat, verified directly against the installed fastmcp 3.4.2: `run_recipe`,
  `generate_mapping`, and `validate_recipe` are plain (synchronous) functions dispatched to a
  worker thread, and FastMCP's threadpool dispatch (`anyio.to_thread.run_sync`, default
  `abandon_on_cancel=False`) does not actually preempt a stuck `generate_data()` call there — the
  same was already true of the old SIGALRM `time_limit()` under FastMCP 3.x's threadpool dispatch
  (see the now-deleted `tests/test_core_timeout.py`'s own regression test for that), so this is
  not a regression from previously-working protection. `iterative_recipe_gen` (an `async def`
  tool) *does* get newly-effective, genuinely-preemptive timeout coverage — previously it had
  none at all.

See `FASTMCP3_REFACTOR_PLAN.md` Phase 5 for the full rationale.

- **`list_capabilities`'s duplicated `limits` block is gone** — `timeout_seconds`,
  `max_capture_chars`, `max_reps`, and `max_target_count` used to appear twice in the response:
  once as top-level scalar fields, and again, identically, nested under `"limits"`. The
  top-level copies are removed; `"limits"` is now the single source of truth for these four
  fields. Any client reading e.g. `payload["max_reps"]` directly (instead of
  `payload["limits"]["max_reps"]`) needs updating.
- **Several discovery tools now advertise a real `outputSchema`** — `list_capabilities`,
  `list_examples`, `get_example`, and `search_docs` previously had bare `dict[str, Any]` return
  annotations, which FastMCP advertises as a generic `{"type": "object", "additionalProperties":
  true}` schema with no field-level shape. They now return `TypedDict`s (`CapabilitiesResult`,
  `ExampleListResult`, `ExampleResult`, `DocsSearchResult`), so `outputSchema` in `tools/list`
  now reflects their real fields. The raw wire-level `structuredContent` payload for these tools
  is unchanged. This *is* observable to callers using `fastmcp.Client`'s typed convenience layer,
  though: when a tool advertises a non-`Union` object schema, `Client.call_tool(...).data` is
  now parsed into a dynamically generated dataclass instead of being handed back as a plain
  `dict` (`fastmcp.Client` itself decides this from the advertised schema, not anything this
  server controls directly) — code doing `result.data["field"]` needs to switch to
  `result.data.field` for these four tools. `analyze_recipe` and `generate_mapping` are
  similarly typed now (`AnalyzeResult`, `MappingResult`, mirroring `run_recipe`'s existing
  `RunResult`) but keep `ToolResult` in their return-type union, so `Client.call_tool(...).data`
  continues to hand back a plain `dict` for those two, unchanged from before.
- **Every tool now declares `ToolAnnotations`** — purely advisory metadata (`readOnlyHint`,
  `idempotentHint`, `openWorldHint`) with no effect on tool behavior or wire payload shape;
  callers that introspect `tools/list`'s `annotations` field will see it populated where it was
  previously always absent.

See `FASTMCP3_REFACTOR_PLAN.md` Phase 6 for the full rationale. `iterative_recipe_gen`'s return
type deliberately stays a bare `str` in this phase; introducing a typed `RecipeGenResult` is
scoped as a separate, higher-risk follow-up PR (see Phase 6, step 4).

- **`run_recipe`'s `capture_output` parameter changed from `bool` to `"preview" | "full" | "none"`,
  and its default no longer inlines the full (up to `max_capture_chars`) captured output.**
  Previously `capture_output=True` (the default) returned the complete captured output inline in
  `stdout_text`, truncated at a raw character offset (which could also corrupt JSON — a truncated
  `output_format="json"` response was not guaranteed to still parse). The complete output has
  always *also* been written to disk and exposed via the returned resource URI regardless of this
  setting, so the old default paid a real, often-unnecessary token cost on every call. The new
  default, `"preview"`, returns a small preview (bounded by the new `SNOWFAKERY_MCP_PREVIEW_CHARS`
  limit, default 2000 chars) plus two new response fields — `output_bytes` (the full artifact's
  size on disk) and `record_count` (total records generated, for `output_format="json"` only, else
  `null`) — so a caller can tell how much data exists without paying to see all of it; the full
  resource read is always available for that. `capture_output="full"` restores the old
  "everything inline" behavior (still bounded by `max_capture_chars`), and `capture_output="none"`
  is unchanged (no inline text at all). Truncation for `output_format="json"` now always drops
  whole trailing records and re-serializes rather than slicing raw characters, so a truncated JSON
  response is always valid JSON, in both `"preview"` and `"full"` modes. Old callers passing a
  literal `true`/`false` will get a client-side schema validation error and need to switch to the
  new string values. `list_capabilities`'s `limits` object gained a matching `preview_chars` field.
- **Fixed a pre-existing bug** (reproduces identically on `main` before this refactor, unrelated to
  the fastmcp version bump): `run_recipe` with an image/diagram `output_format` (`svg`/`svgz`/
  `dot`/`png`/`jpeg`) and any non-`"none"` `capture_output` crashed with
  `ValueError: I/O operation on closed file`, because Snowfakery's own `generate_data()` closes
  the in-memory output buffer it's handed once rendering finishes for these formats. `run_recipe`
  now falls back to reading the artifact straight off disk for these formats instead of crashing.

- A **real release** (GitHub Release + attached artifacts + PyPI publish) happens on **pushing a git tag** matching `v*`.
- A **manual run from the GitHub UI** (`workflow_dispatch`) is supported as a **dry run build**: it builds + (optionally) tests and uploads build artifacts to the workflow run, but it does **not** create a GitHub Release or publish to PyPI.

## Prereqs (local)

- `uv` installed
- Submodule initialized (recommended for local dev/tests):
	- `git submodule update --init --recursive`

## Versioning + tags

- Source of truth version: `pyproject.toml` → `[project].version`
- Release tag format: `vX.Y.Z` (example: `v0.2.0`)
- The release workflow enforces: `tag version == pyproject.toml version`

## Standard release process (recommended)

1. **Update version**
	- Edit `pyproject.toml` and bump `[project].version`.

2. **Run tests locally**
	- `uv sync --all-groups`
	- `uv run pytest`

3. **Land the version bump on `main`**
	- Commit and push the change (PR preferred).

4. **Create and push a tag** (this triggers the release workflow)
	- Annotated tag (recommended):
		- `git tag -a vX.Y.Z -m "vX.Y.Z"`
		- `git push origin vX.Y.Z`
	- Lightweight tag also works:
		- `git tag vX.Y.Z`
		- `git push origin vX.Y.Z`

5. **Monitor GitHub Actions**
	- The `Release` workflow will:
		- checkout submodules
		- run tests
		- build wheel + sdist (`uv build`)
		- build a `.mcpb` bundle (via reusable `build-mcpb.yml` workflow)
		- attach `dist/*` + `release-assets/*` + `mcpb/*` to a GitHub Release (release notes auto-generated)
		- publish `dist/*.whl` + `dist/*.tar.gz` to PyPI via Trusted Publishing (tags only)
		- publish server metadata to MCP Registry (tags only)

## Can I release via the GitHub UI?

Yes — *as long as the UI action creates/pushes the git tag*.

Two common UI paths:

1) **Create a tag in the UI**

- Go to the repo → **Releases** → **Draft a new release**
- Enter a tag like `vX.Y.Z` and choose the target commit (usually `main`)
- Publish the release

This creates the git tag (`refs/tags/vX.Y.Z`), which should trigger the `on: push: tags: ["v*"]` workflow.

2) **Run the workflow manually (UI)**


- Go to **Actions** → **Release** → **Run workflow**

This is useful to verify that builds/tests pass on GitHub runners. It will upload build artifacts to the workflow run, but it will not create a GitHub Release nor publish to PyPI because those steps only run on tag pushes (`refs/tags/v*`).

## What artifacts are produced?

On tag releases, the GitHub Release will include:

- `dist/*.whl` (wheel)
- `dist/*.tar.gz` (sdist)
- `release-assets/*.mcpb` (experimental MCP bundle)

On workflow_dispatch dry runs, the workflow uploads artifacts to the run:

- `pypi-dist/` (wheel + sdist only)
- `release-assets/` (experimental `.mcpb`, `THIRD_PARTY_NOTICES.md`, SBOM)

## Troubleshooting

### Tag/version mismatch

If the workflow fails at “Check tag matches pyproject version”, update `pyproject.toml` to match the intended release version (or retag). The workflow requires exact equality.

### Fixing a broken release tag

If you pushed a bad tag and need to redo it:

- Delete the tag locally: `git tag -d vX.Y.Z`
- Delete the remote tag: `git push origin :refs/tags/vX.Y.Z`
- Fix the code/version, then recreate and push the tag.

(If a GitHub Release was created, delete it in the UI too.)

### PyPI Trusted Publishing setup

The publish job uses OIDC Trusted Publishing (`pypa/gh-action-pypi-publish`). If PyPI isn’t configured to trust this GitHub repo/environment yet, the publish step will fail.


### MCP Registry Publishing

The release workflow automatically publishes server metadata to the MCP Registry after a successful PyPI publish. This uses:

- **server.json**: Contains the MCP Registry metadata (name, description, packages, etc.)
- **manifest.json**: Contains the `mcpName` field that matches the server name in `server.json`
- **GitHub authentication**: Uses pre-authenticated credentials stored as a GitHub Actions secret

The server is published under the namespace `io.github.composable-delivery/snowfakery-mcp`, which is verified against the GitHub organization ownership.

#### Setting up MCP Registry Authentication

The `mcp-publisher` tool uses an interactive OAuth device flow for GitHub authentication, which doesn't work in CI/CD. To enable automated publishing:

1. **Authenticate locally** (one-time setup):
   ```bash
   mcp-publisher login github
   ```
   Follow the prompts to complete the OAuth device flow.

2. **Locate credentials file**:
   The credentials are typically stored in `~/.mcp-publisher/credentials.json` or `~/.config/mcp-publisher/credentials.json`

3. **Add to GitHub Actions secrets**:
   - Go to repository Settings → Secrets and variables → Actions
   - Create a new secret named `MCP_REGISTRY_CREDENTIALS`
   - Paste the contents of the credentials file

4. **Verify in workflow**:
   The release workflow will restore these credentials before publishing to the registry.
