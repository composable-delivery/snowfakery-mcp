# Recommended Plan: FastMCP 2.14.3 → 3.4.2 Refactor

This is the recommended initial execution plan for migrating `snowfakery-mcp` off the
currently-pinned `fastmcp>=2.14.3` onto the latest FastMCP 3.x (**3.4.2**), and adopting the
highest-value framework capabilities identified in `FASTMCP3_REFACTOR_IDEAS.md`.

It was produced by drafting two independently-framed candidate plans (a safety-first
incremental approach and an ambitious "rebuild on 3.x idioms in one pass" approach), having a
synthesis pass judge, merge, and correct them against this repo's actual CI/test constraints,
and then revising the earliest phase after review: the first draft staged the bug fixes and
test hardening on the *old* 2.14.3 pin before bumping, on a bisectability argument that didn't
actually hold up here (see "Why the bump comes first" below) — so that staging was dropped in
favor of doing the bump immediately.

## Philosophy

> Bump straight to fastmcp 3.4.2 — the destination version — fixing the pre-existing
> Context-API bugs and hardening the test safety net directly against it in the same pass, since
> there's no marginal safety benefit to doing that work twice against two different versions.
> Then layer every subsequent 3.x-idiom improvement (composable lifespan, typed I/O,
> `ToolAnnotations`, `timeout=`, middleware) as its own small, single-theme, independently
> revertible PR rather than one large simultaneous rebuild.

In a CI-gated production repo (75% coverage gate, mypy strict, PyPI + MCP registry publish
pipeline), the cost of occasionally re-touching the same `register_*` signature line across two
later PRs is far smaller than the cost of one enormous PR where a regression can't be bisected
to a single cause. That principle still drives the phase split from Phase 2 onward — it just
doesn't extend to artificially delaying the version bump itself.

### Why the bump comes first (not staged on 2.14.3)

FastMCP's own migration guide states plainly that "most users will not need to change their
code at all" going from 2.x to 3.x, and this repo's actual `@mcp.tool`/`@mcp.resource`/
`@mcp.prompt` call sites confirm it — grep shows every one of them passes only `tags={...}` (or
a bare URI), with zero usage of any kwarg that changed shape across the boundary. The three bugs
being fixed here (`ctx.sample()` result parsing, two `ctx.read_resource()` interpolation sites)
are plain Python logic errors — `Context.sample()` returning `SamplingResult` and
`Context.read_resource()` returning `list[ReadResourceContents]` were independently confirmed
identical on both the installed 2.14.3 and (via the review that produced this plan) 3.4.2. These
aren't migration-shaped bugs that need a stable baseline to diagnose; they're independent of the
version pin entirely.

Given that, staging them on the old pin first didn't actually buy the isolation it promised:
verifying the rewritten tests pass against 2.14.3 doesn't tell you anything about 3.4.2 unless
you already trust API stability across the bump — and if you're trusting that (which the
evidence above supports), there's no reason to gate on the old version at all. Writing and
verifying the tests directly against 3.4.2 is the more rigorous move, since that's the real
target contract, not a proxy for it. Bundled together, the two failure modes are also easy to
tell apart in practice: a version-bump break tends to show up as fixture-level breakage (the
shared `mcp_client` fixture failing, taking most of the suite down with it) or import/
registration errors, while a bad bug-fix shows up as one specific test's assertion failing —
different enough signatures that bisecting a red CI doesn't actually require two separate merged
PRs. For a moment-to-moment sanity check while developing, it's still fine to apply the bug
fixes and test rewrites first against your currently-installed 2.14.3 venv, confirm green
locally, and *then* bump the pin and re-run to see what the bump alone changes — that's a
two-minute local check worth doing, just not a gate that needs its own PR and CI cycle.

### Why still not the ambitious draft's single mega-phase

The ambitious draft's single large phase — composable lifespan + typed I/O + `ToolAnnotations` +
`timeout=` + middleware + error contracts, ~12 files, all at once — is still rejected as the
organizing structure for the *post-bump* work. It stacks the highest-risk architectural refactor
in the whole migration (threading `ctx.lifespan_context` through every registration function) on
top of several other simultaneously-changing behaviors (wire-level error semantics, output
schemas, timeout mechanics) with independent risk profiles — if something breaks, there are too
many candidate causes at once. Two ideas *were* grafted in from that draft, plus one bug found by
re-reading the source during synthesis:

- **`timeout=` is resolved at decoration time**, inside `create_app()`, before any
  lifespan/request context exists — it structurally cannot be sourced from
  `ctx.lifespan_context`. Phase 4 below explicitly carves out one pre-lifespan `timeout_seconds`
  scalar for the four tools that need it, so Phase 5 has a clean, already-anticipated slot
  instead of hitting this conflict mid-implementation.
- **A second instance of the `ctx.read_resource()` bug** exists inside `tools/agentic.py`
  itself (the schema-context fetch near the top of `_iterative_recipe_gen_impl`), not just in
  `prompts.py`'s `author_recipe`. Both sites are fixed together in Phase 1.

---

## Phase 1 — Bump to fastmcp 3.4.2, fixing the live Context-API bugs and hardening the test safety net in the same pass

**Goal:** Land `fastmcp>=3.4.2` directly, fix the three real Context-API bugs against the target
version, and close the exact test blind spots (mocked `Context`/`FastMCP` that don't reflect the
real API shapes) that let those bugs ship undetected — all as one continuous pass, since none of
this work is meaningfully separable from the bump given how stable the surface API is across the
boundary (see "Why the bump comes first" above).

**Steps:**
1. Bump `fastmcp>=2.14.3` → `fastmcp>=3.4.2` in `pyproject.toml`; run `uv lock` (confirmed
   `uv.lock` currently pins `version = "2.14.3"` exactly — editing the pyproject spec alone does
   **not** move the resolved version) and inspect the diff for both fastmcp's resolved version
   and the transitively-pulled `mcp` SDK version.
2. In `snowfakery_mcp/tools/agentic.py`'s `_iterative_recipe_gen_impl`, replace the
   `getattr(result, "content", None)`/`hasattr`/`isinstance` unwrapping chain with
   `current_recipe = (result.text or "").strip()`, matching `Context.sample()`'s real
   `SamplingResult(.text/.result/.history)` contract (confirmed directly against both the
   installed 2.14.3 package and 3.4.2). Keep the existing markdown-fence-stripping logic that
   follows.
3. In the same function's earlier schema-context fetch (`schema = await
   ctx.read_resource(...)`), fix the identical bug at that call site: today
   `first_content.text += f"...{schema}"[:2000]` interpolates the raw `list[ReadResourceContents]`
   repr into the prompt sent to the LLM. Extract and join each item's `.content` before
   truncating/interpolating. **Do not skip this** because `prompts.py`'s instance looks like the
   only one.
4. In `snowfakery_mcp/prompts.py`'s `author_recipe`, apply the same fix.
5. Rewrite `tests/test_agentic.py`'s mocks: stop returning `mcp.types.CreateMessageResult`
   (which happens to have `.content` and masks the bug) and construct real `SamplingResult`
   instances, or drive the real tool end-to-end.
6. Add a new test using `fastmcp.Client(server_app, sampling_handler=fake_handler)` that calls
   the real, decorator-registered `iterative_recipe_gen` over the in-memory transport and
   asserts the returned text is the handler's YAML, not a dataclass repr.
7. Add a success-path assertion to `tests/test_prompts_extended.py` driving `author_recipe`
   through the real `mcp_client` fixture, asserting the rendered text contains real schema JSON
   (e.g. a `"$schema"` key) — today's only coverage exercises solely the exception branch.
8. Rewrite `tests/test_resources_static_unit.py`, `test_tools_examples_extended.py`, and
   `test_resources_templates.py` to register against a real `fastmcp.FastMCP("test")` instance
   instead of `MagicMock(spec=FastMCP)`, driving branch coverage (dev-mode-vs-bundled schema
   path, Traversable-vs-Path examples root, path-traversal in templates) through real
   `fastmcp.Client` calls and asserting on `CallToolResult`/`ToolResult(is_error=True)` instead
   of the bypassed raw function.
9. Split `[[tool.mypy.overrides]]` so `ignore_missing_imports=true` applies only to
   `snowfakery.*`; run `uv run mypy snowfakery_mcp` and triage every newly-surfaced error against
   fastmcp's real 3.4.2 stubs.
10. Grep for `FastMCP.get_tools()`/`get_resources()`/`get_prompts()` dict-returning accessor
    usage (removed in later fastmcp versions) — confirm zero matches, documenting this as a
    verified non-issue rather than an assumption.
11. Add a "Local development" section to `CONTRIBUTING.md` documenting `fastmcp dev inspector
    snowfakery_mcp/server.py:mcp` — the confirmed 3.4.2 command-group form (`dev` is now a group
    with `apps`/`inspector` subcommands, unlike 2.x's bare `fastmcp dev <server-spec>`).
12. Re-run `ruff check`/`format --check` and `scripts/generate_third_party_notices.py --check`,
    regenerating the notices file since it enumerates fastmcp's transitive dependency tree.
13. Add a `package-ecosystem: "uv"` block to `.github/dependabot.yml` alongside the existing
    `github-actions` entry, so this migration's own trigger (nothing today ever proposes a
    fastmcp upgrade PR) doesn't recur silently for future majors.
14. Push and require the full CI matrix (3.12 + 3.13, coverage gate, lint, mypy, compliance,
    mcpb bundle build) green before merging.
15. **Do not** add any new fastmcp 3.x-only *feature* usage (`ToolResult`, middleware,
    `output_schema=`, `timeout=`, `task=`) in this PR beyond what the bug fixes above require —
    keep the diff to the bump + bug fixes + test hardening. Those features are Phases 2–7.
16. Manually smoke-test the packaged console script once over real stdio (`uv run
    snowfakery-mcp`), since CI's in-memory `Client` transport never exercises the actual stdio
    subprocess boundary real MCP clients use.

**Testing strategy:** Acceptance: (a) full suite green against 3.4.2; (b) for each of the three
bug fixes, temporarily revert the 1–3 line production fix locally and confirm the new/rewritten
test fails, proving it actually detects the bug rather than rubber-stamping; (c) 75% coverage
gate holds (real-`Client` tests typically cover more branches than mocked decorator-capture
tests); (d) mypy clean against fastmcp's real stubs. For local iteration, it's reasonable to
apply the bug fixes and test rewrites first against your already-installed 2.14.3 venv, confirm
green, then bump the pin and re-run to see what changes from the bump alone — a quick sanity
check, not a required gate.

**Risk:** Low-medium. The three production bug fixes are each 1–3 lines and version-independent
(confirmed identical behavior needed on both 2.14.3 and 3.4.2); the version bump itself remains
the source of any real surprise (the `lifespan=` contract, `Client` transport internals, the
exact post-bump shape of `Context.read_resource()` — re-verify it didn't change rather than
assuming Phase 1's fixes are final). If CI goes red and it's unclear whether the bump or a bug
fix is at fault, bisect locally (stash the bug-fix/test changes, re-run against the bump alone)
rather than reaching for a separate merged PR.

**Effort:** Medium-Large (~4–6 days) — combines mechanical bug/test work with the version-bump
triage; wide blast radius since nearly every file in `snowfakery_mcp/` imports fastmcp or
`mcp.types`.

---

## Phase 2 — Fix resource/tool content-type and path-safety correctness bugs

**Goal:** Fix three small, independent, low-risk bugs surfaced alongside the migration: binary
run artifacts crash on forced UTF-8 decode, the recipe schema is double-JSON-encoded and
mislabeled as `text/plain`, and `templates.py` reimplements path-traversal protection instead
of reusing the already-tested helper.

**Steps:**
1. In `resources/runs.py`'s `run_artifact_resource`, branch on file extension: for binary
   formats (`.png`, `.svgz`, etc.), read bytes and return via FastMCP's bytes-aware
   `ResourceContent`/`ResourceResult` with an explicit `mime_type=...`; keep the existing text
   path for `.txt`/`.json`/`.sql`/`.dot`/`.svg`/`.yml`.
2. In `tools/docs.py`'s `get_schema`, `json.loads()` the schema file and return the parsed dict
   directly instead of nesting it as an escaped string.
3. In `resources/static.py`'s `recipe_schema_resource`, add `mime_type="application/json"` —
   directly benefits the Phase-1-fixed `author_recipe` prompt and `iterative_recipe_gen`, both
   of which read this exact resource.
4. In `resources/templates.py`'s `get_template`, replace the inline `resolve()`/`relative_to()`/
   bare `except ValueError` block with a call to `paths.ensure_within(...)` — the same helper
   `resources/runs.py` already uses — preserving the existing error contract so
   `tests/test_resources_templates.py`'s assertions don't need to change.
5. Do **not** attempt the larger Provider-subclass consolidation across
   `static.py`/`templates.py`/`runs.py` in this phase (see Non-Goals).

**Testing strategy:** Add an end-to-end test running `run_recipe(output_format="png")` through
`mcp_client` and reading back the diagram resource, asserting real binary content instead of a
`UnicodeDecodeError`; extend schema tests to assert `get_schema()`'s structured content is
already a parsed dict and the resource reports `mimeType == "application/json"`; re-run the
existing template-security test unchanged to confirm `ensure_within` preserves the identical
error contract.

**Risk:** Low — each fix is file-local and behavior-additive. The one observable change is
`get_schema`'s/the schema resource's payload shape (parsed dict vs. double-encoded string) —
note as a small wire-format change in release notes.

**Effort:** Small (~1 day).

---

## Phase 3 — Standardize tool error contracts with `ToolResult(is_error=...)`

**Goal:** Replace the three copy-pasted hand-rolled error dicts with the protocol-native
`isError` signal, remove the synthetic result-wrapper around Union-typed returns, and close
`analyze_recipe`'s one genuinely unhandled-exception gap.

**Steps:**
1. In `core/types.py`, delete the unused `ErrorLocation` TypedDict (zero callers) and add a
   shared helper (e.g. `core/errors.py`) replacing the identical `DataGenError`/
   `OperationTimeout`/`(OSError, RuntimeError, ValueError)` trio duplicated in `tools/run.py`,
   `tools/mapping.py`, and `core/validate.py`.
2. Update `run_recipe`, `generate_mapping`, and `validate_recipe_logic` to call the shared
   helper and return `ToolResult(structured_content={...}, is_error=True)` on failure. Verify
   live over an in-memory `Client` against the post-Phase-1 fastmcp 3.4.2 resolution that this
   correctly sets `CallToolResult.isError` before relying on it in tests (today it's always
   `False` for these tools).
3. Add explicit `output_schema=` to `run_recipe`/`generate_mapping`/`validate_recipe`'s
   registrations to eliminate the synthetic `{"result": {...}}` envelope.
4. Wrap `analyze_recipe`'s `parse_recipe()` call — currently zero try/except — so a malformed
   recipe returns `ToolResult(is_error=True, ...)` instead of an uncaught exception crossing the
   transport.
5. Register `fastmcp.server.middleware.error_handling.ErrorHandlingMiddleware` in
   `create_app()` as an outer backstop for exceptions that still escape a tool entirely.

**Testing strategy:** Update existing error-path assertions to check `result.is_error is True`
via the real `mcp_client` fixture instead of only `structured_content["ok"]`; add a test calling
`analyze_recipe` with broken YAML and asserting it now returns a structured error rather than an
uncaught exception; add a focused unit test for the shared error helper. Re-check the coverage
gate after deleting ~40 duplicated lines.

**Risk:** Medium — this changes the wire-level `isError` flag and removes the result envelope,
both observable, intentional behavior changes for any client inspecting `structured_content["ok"]`
or unwrapping `.result`. Document as a deliberate breaking change in `RELEASE.md`.

**Effort:** Medium (~2–3 days).

---

## Phase 4 — Fix the `create_app()`/`lifespan()` split-brain; delete dead `_ServerState`

**Goal:** Replace the two independently-constructed `WorkspacePaths`/`Config` copies with a
single lifespan-owned source of truth read via `ctx.lifespan_context`, and delete the
fully-vestigial `_ServerState`/`get_paths()`/`get_config()` (confirmed zero external callers).

**Steps:**
1. Replace `create_app()`'s and `lifespan()`'s independent construction with a single
   lifespan-decorated async generator yielding `{"paths": paths, "config": config}`.
2. Change every `register_*` function across `tools/*.py`/`resources/*.py` to stop taking
   `paths`/`config` as closure arguments; have the wrapped tool/resource accept `ctx: Context`
   and read `ctx.lifespan_context["paths"]`/`["config"]` at call time.
3. **Deliberate carve-out:** `@mcp.tool(timeout=...)` (added in Phase 5) is resolved at
   decoration time inside `create_app()`, before any lifespan/request context exists, so it
   structurally cannot be sourced from `ctx.lifespan_context`. Keep this narrow: the four tools
   that call `generate_data()` additionally take a plain `timeout_seconds: int` scalar into
   their `register_*` function, sourced from the single `Config.from_env()` call already made
   once in `create_app()` — not a second independently-constructed `Config`. Every other
   config/paths access reads `ctx.lifespan_context` at call time.
4. Delete `_ServerState`, `get_paths()`, and `get_config()`.
5. Update the three Phase-1-hardened test fixtures to supply a lifespan stub yielding
   `{"paths":..., "config":...}` when constructing their real `FastMCP("test")` instance — a
   small, expected follow-up, not a full rewrite.

**Testing strategy:** Largest blast radius by file count (12 files) though each edit is
mechanical. Rely on mypy strict (fastmcp-aware since Phase 1) to catch missed signature updates,
plus the full suite. Add one explicit test asserting `ctx.lifespan_context` actually contains
the expected keys after a real server startup.

**Risk:** Medium — touches nearly every registration function's signature; the main risk is a
tool silently receiving stale/`None` paths or config if a call site is missed, or mishandling
the `timeout_seconds` carve-out. Ship as one atomic PR — a half-migrated state is worse than
either extreme.

**Effort:** Medium (~2–3 days, mostly mechanical repetition).

---

## Phase 5 — Replace SIGALRM `time_limit()` with per-tool `timeout=`

**Goal:** Replace the main-thread-only, silently-no-op-off-Unix SIGALRM timeout with FastMCP
3.x's cross-platform `timeout=`, closing the gap that `iterative_recipe_gen` has zero timeout
coverage today.

**Steps:**
1. Delete `core/timeout.py`'s `time_limit()` and `OperationTimeout`.
2. Add `timeout=timeout_seconds` (the Phase-4 pre-lifespan scalar) to the registrations for
   `run_recipe`, `generate_mapping`, `validate_recipe`, and `iterative_recipe_gen`.
3. Remove the `with time_limit(...)` blocks in `tools/run.py`, `tools/mapping.py`,
   `core/validate.py`.
4. Update the Phase-3 shared error helper to translate a timeout-triggered `McpError` into the
   existing `ToolError` shape, preserving current field naming where possible.
5. Delete `tests/test_core_timeout.py`'s SIGALRM-specific tests (dead code once removed).

**Testing strategy:** Add a test that monkeypatches `generate_data` to sleep past a
deliberately short configured timeout and asserts the call surfaces a timeout error within a
bounded, non-flaky window — avoid real multi-second sleeps or SIGALRM-specific platform quirks.

**Risk:** Medium — intentional behavior change (`McpError`-shaped timeout vs. the custom
`OperationTimeout` dict) needing release notes. Honest caveat: `anyio.fail_after` cancels the
*await*, not the dispatched worker thread — a genuinely stuck native call can keep running in
the background after the client sees a timeout. A portability/concurrency improvement, not true
preemption — document accordingly.

**Effort:** Medium (~1–2 days).

---

## Phase 6 — Typed result contracts and `ToolAnnotations` for every tool

**Goal:** Replace remaining `dict[str, Any]`/bare-`str` return annotations with typed models,
and declare `ToolAnnotations` on every tool — merged into one phase since both are purely
additive, zero-execution-risk changes touching the identical file set.

**Steps:**
1. Add TypedDicts for `CapabilitiesResult`, `ExampleListResult`/`ExampleResult`,
   `DocsSearchResult`, `AnalyzeResult`, and `MappingResult` (mirroring `RunResult`) in
   `core/types.py`.
2. Update the return-type annotations of `list_capabilities`, `list_examples`/`get_example`,
   `search_docs`, `analyze_recipe`, `generate_mapping` accordingly; fix `list_capabilities`'
   duplicated limits block while touching that function.
3. Add `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` to the discovery/analysis
   tools; `readOnlyHint=False, idempotentHint=False` to `run_recipe`/`generate_mapping`;
   `openWorldHint=True` to `iterative_recipe_gen` (return type stays `str` in this phase).
4. As a **separate, explicitly higher-risk follow-up PR** (not bundled here), introduce a
   `RecipeGenResult` TypedDict for `iterative_recipe_gen` and change its return type from bare
   `str` — call out that any client pattern-matching on `"Error during generation:"` text needs
   updating, since this is a genuine breaking wire-shape change unlike everything else here.
5. Opportunistically add `version="1"` to the registrations touched in this phase — cheap
   insurance, not a blocking requirement.

**Testing strategy:** Update integration test assertions to check specific typed fields instead
of loose `assert key in payload`; add an explicit `output_schema` assertion via
`mcp_client.list_tools()`; extend the tool-listing test to assert on annotation fields for a
representative sample.

**Risk:** Low for discovery-tool typing and annotations (advisory hints only). Medium, isolated
to the separate `RecipeGenResult` follow-up PR.

**Effort:** Medium (~2 days, plus ~0.5–1 day for the separate follow-up PR).

---

## Phase 7 — Baseline observability middleware

**Goal:** Give every call per-call visibility and a defense-in-depth output-size backstop, with
zero tool-code changes.

**Steps:**
1. Register `LoggingMiddleware` (or `StructuredLoggingMiddleware`) in `create_app()`.
2. Register `TimingMiddleware`, giving visibility into actual elapsed time vs. the Phase-5
   `timeout=` limit.
3. Register `ResponseLimitingMiddleware(max_size=...)` sized generously above
   `Config.max_capture_chars`, as a backstop for tools with no size cap today.

**Testing strategy:** Add a smoke test confirming a normal `run_recipe` call still returns
identical structured content with middleware installed; manually verify during a local
`uv run snowfakery-mcp` session that log output stays on stderr and never touches stdout.

**Risk:** Low — purely additive with no tool-code changes; the one thing to explicitly verify,
not assume, is that logging never writes to stdout under stdio transport.

**Effort:** Small (~1 day).

---

## Migration Checklist

Concrete, codebase-specific items to verify during Phase 1 (derived from FastMCP's full 2.x→3.x
breaking-changes list, filtered to what actually applies here):

- `mcp: FastMCP = create_app()` and `FastMCP(name=..., instructions=..., lifespan=lifespan)` —
  grep-confirmed the only three constructor kwargs used anywhere (no `auth=`, `tags=`,
  `version=` at the `FastMCP()` level); confirm unchanged in 3.4.2.
- The `@asynccontextmanager async def lifespan(...)` pattern currently yields `None`, not a
  context dict — confirm 3.4.2 still accepts a plain contextmanager-based `lifespan=` before
  Phase 4 adopts the composable, dict-yielding form.
- Every `@mcp.tool`/`@mcp.prompt`/`@mcp.resource` call site passes only `tags={...}` (or a bare
  URI) — zero usages of `name=`, `description=`, `output_schema=`, `annotations=`, `version=`,
  `enabled=`, or the 3.x-only `task=` today, so there's no kwarg-rename surface to fix
  pre-migration, only a contract to re-verify via Phase 1's real-Client tests.
- `Context.sample()` confirmed to return `SamplingResult` (`.text`/`.result`/`.history`) on both
  2.14.3 and 3.4.2 — the code's bug is pre-existing, independent of the bump, fixed in Phase 1.
- `Context.read_resource()` confirmed to return `list[ReadResourceContents]`, never a string, at
  **both** call sites (`prompts.py` and `agentic.py`) on both versions — still worth a final
  re-check against whatever fastmcp actually resolves to at bump time rather than assuming it's
  unchanged, since this is exactly the kind of Context surface most likely to shift across a
  major version; don't port the Phase 1 unwrapping code forward blindly.
- `mcp.types.SamplingMessage`/`TextContent`/`CreateMessageResult` come from the separate `mcp`
  SDK package fastmcp depends on transitively — confirm the version pulled in by
  `fastmcp>=3.4.2` still exports these exact names/fields.
- `fastmcp.Client(server_app)` + `async with client:` in-memory transport (the `mcp_client`
  fixture) — the single highest-leverage compatibility surface to verify first, since a change
  here silently fails most of the safety net at once.
- The defensive `hasattr(result, 'data')`/`.structured_content`/`.content` branching in
  `_tool_result_text()`/`_resource_text()`/`get_tool_data()` — a `CallToolResult` shape change
  could silently route through a different branch instead of failing loudly; manually spot-check
  extracted values after the bump rather than trusting a green checkmark alone.
- `FastMCP.get_tools()`/`get_resources()`/`get_prompts()` dict-returning accessors — grep-
  confirmed zero call sites anywhere in this codebase, so this is a verified-safe/inapplicable
  breaking change, not something requiring a fix.
- `fastmcp dev <server-spec>` CLI shape changed to a command group in 3.4.2 — confirmed
  `CONTRIBUTING.md`/`README.md` document no `fastmcp dev`/`run`/`inspect`/`install` invocation
  today, so nothing is broken, but Phase 1 must not introduce the old 2.x-style bare invocation.
- `[[tool.mypy.overrides]]` for `fastmcp.*` gives zero static signal today — Phase 1 must split
  this override and triage every newly-surfaced error.
- `mcp.run()` bare zero-argument call in `server.py:run()` — the sole way both the packaged
  console script and the `.mcpb` bundle launch the server — confirm the zero-arg stdio default
  is unchanged in 3.4.2.
- The `.mcpb` bundle build and PyPI/MCP-registry publish workflows — grep-confirmed neither
  hardcodes nor introspects the fastmcp version string; only
  `scripts/generate_third_party_notices.py --check` needs regeneration.
- `Client[Any]` generic-subscript annotations in test files — confirm `fastmcp.Client` remains
  subscriptable/Generic in 3.4.2 once the mypy override is removed.
- `@mcp.tool(timeout=...)` (Phase 5) is resolved at decoration time, before any lifespan/request
  context exists — Phase 4's lifespan refactor must preserve the pre-lifespan `timeout_seconds`
  scalar carve-out rather than attempting to route it through `ctx.lifespan_context`.
- `ToolResult(structured_content=..., is_error=True)` (Phase 3) is claimed to correctly set
  `CallToolResult.isError` — re-verify live over an in-memory `Client` against the actual 3.4.2
  resolution before relying on it in Phase 3's tests.

## Non-Goals (deliberately deferred, with reasons)

- **Streaming progress via `ctx.report_progress` + echo forwarding** (idea #17) — requires
  bridging synchronous `generate_data()` into async `Context` via `anyio.from_thread`, a real
  coupling to FastMCP's threadpool internals the idea itself flags as a risk to watch. Revisit
  once Phases 1–5 are stable.
- **`pydantic-settings` migration for `Config`** (#18) — pure hygiene, no bug fixed, real risk of
  silently changing clamp-not-raise behavior tests currently assert. If picked up later, the
  acceptance bar is that `test_core_config.py` passes byte-for-byte unmodified.
- **Elicitation / capability-gated visibility / session state for `iterative_recipe_gen`** (#19)
  — explicitly speculative and client-support-dependent; future exploratory work behind a flag.
- **`FileUpload` provider** (#20) — zero benefit to the server's dominant caller (coding agents
  with direct filesystem access); deferred as a future feature request.
- **Auth-provider bootstrap + tag-based authorization** (#21) — `AuthMiddleware` no-ops on
  stdio, the server's only transport today; zero present-day effect. Deferred until HTTP
  deployment is planned (see #22, also deferred).
- **Opt-in HTTP/streamable-http transport** (#22) — additive, no current driver; would also need
  #21's auth story solved first, since `run_recipe` executes YAML with no access control today.
- **Approval gate before `run_recipe`** (#24) — soft, convention-based, no server-enforced
  guarantee; real safety already comes from `Config`'s hard limits.
- **OpenTelemetry tracing toggle** (#25) — the most marginal idea for a single-user local stdio
  subprocess; Phase 7's `TimingMiddleware` captures most of the practical value far more cheaply.
- **`inline-snapshot`/`dirty-equals` adoption** (#26) — quality-of-life, not a safety-net gap;
  fold in opportunistically whenever Phase 3/6's test files are next touched.
- **`FormInput`-driven goal builder** (#27) — UX scaffolding around an already-working tool, and
  its synchronous `on_submit` doesn't cleanly compose with the async sampling loop.
- **Background Tasks (`task=True`)** (#28) — explicitly an evaluate-and-prototype item, not a
  guaranteed win; requires async conversion, a new extra, and newer client-side polling support.
  Deferred as a separate research spike after the bump is stable.
- **Tool versioning with `version=`** (#29) — folded in opportunistically as an optional Phase 6
  sub-step rather than its own phase.
- **`Context.list_roots()` consultation** (#30) — speculative and client-dependent per its own
  framing; deferred, not required for migration correctness.
- **Full Provider-subclass consolidation** (the stretch half of idea #12) — only the cheap
  quick-win (Phase 2: `templates.py` reusing `ensure_within`) is included here. The full
  consolidation would require rewriting resource registration for uncertain payoff, since
  FastMCP's built-in Provider subclasses aren't drop-in replacements for this codebase's bespoke
  path-safety needs. Best attempted, if ever, once the post-Phase-4 resource signatures have
  stabilized in production use.
