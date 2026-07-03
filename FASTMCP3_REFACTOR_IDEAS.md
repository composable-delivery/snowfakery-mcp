# FastMCP 3.x Refactor Ideas

This document catalogs refactor opportunities for migrating `snowfakery-mcp` from the
currently-pinned `fastmcp>=2.14.3` to the latest FastMCP 3.x (**3.4.2** as of this writing),
and for making fuller use of what the framework now provides. Ideas are ordered from most to
least valuable — every idea below has *some* genuine value, but they trade off differently on
impact, effort, and risk.

This list was produced by a multi-agent review: 8 independent "lenses" (typed I/O, Context
runtime features, composition/providers, deployment/transport, middleware/observability,
testing/DX, Apps/UI, and auth/security) each proposed ideas grounded in the real FastMCP 3.x
API surface; the results were deduplicated, scored, adversarially fact-checked against the
installed FastMCP packages, and checked for gaps by an independent completeness critic. The
top two findings (ranks #1 and #3) were independently re-verified against this repo's actual
source and the installed `fastmcp` package before writing this doc — both are real, live bugs
in the code as it stands today, not hypothetical migration concerns.

For the sequencing recommendation, see `FASTMCP3_REFACTOR_PLAN.md`.

---

## 1. Fix `iterative_recipe_gen`'s broken `ctx.sample()` result parsing — value 10/10

**Files:** `snowfakery_mcp/tools/agentic.py`, `tests/test_agentic.py`, `tests/test_mcp_integration.py`
**Effort:** M · **Risk:** low

`Context.sample()` always returns a `SamplingResult` dataclass (`.text` / `.result` / `.history`)
— confirmed directly against the installed `fastmcp` package, it has never had a `.content`
attribute. `_iterative_recipe_gen_impl`'s parsing chain does `content = getattr(result,
"content", None)`, which is always `None`, so it falls through to `content = str(result)` — the
literal Python dataclass repr — instead of the LLM's generated YAML. **This is broken today**,
against the version already pinned in `pyproject.toml`, not a future migration concern.

Fix: `current_recipe = (result.text or "").strip()`. Pair with a real end-to-end test using
`fastmcp.Client(server_app, sampling_handler=fake_handler)` driving the actual registered tool
over an in-memory transport, and rewrite `tests/test_agentic.py`'s mocks to return real
`SamplingResult` objects instead of `mcp.types.CreateMessageResult` (which happens to have
`.content` and is exactly what hid this bug from CI).

## 2. Standardize tool result contracts: `ToolResult(is_error=...)`, explicit `output_schema=`, centralized error handling — value 9/10

**Files:** `snowfakery_mcp/tools/run.py`, `mapping.py`, `core/validate.py`, `tools/validate.py`, `tools/analyze.py`, `core/types.py`, `server.py`
**Effort:** M · **Risk:** medium

Three fixes bundled because they touch the same tool group:
- `run_recipe`/`generate_mapping`/`validate_recipe` hand-roll `{"ok": False, "error": {...}}`
  instead of `fastmcp.tools.tool.ToolResult(structured_content=..., is_error=True)` — verified
  live that `ToolResult(is_error=True)` correctly sets the protocol-level
  `CallToolResult.isError` flag, which today is **always `False`** even on semantic failure.
- Because `RunResult` is a `Union` type, FastMCP auto-wraps both the advertised schema and the
  actual response in a synthetic `{"result": {...}}` envelope — verified on both 2.14.3 and
  3.4.2. Explicit `output_schema=` removes this extra indirection every client has to unwrap.
- The identical `DataGenError` / `OperationTimeout` / `(OSError, RuntimeError, ValueError)`
  except-block is copy-pasted verbatim in all three files — extract into one shared helper.
- `analyze_recipe` is the one tool with **zero** exception handling — a malformed recipe raises
  straight through to the client. Add a `fastmcp.server.middleware.error_handling.ErrorHandlingMiddleware`
  backstop for exactly this class of gap (not a replacement for the typed-result pattern, which
  is a business-logic contract).

## 3. Fix `author_recipe` prompt's broken `ctx.read_resource()` interpolation — value 8/10

**Files:** `snowfakery_mcp/prompts.py`, `tests/test_prompts.py`, `tests/test_prompts_extended.py`
**Effort:** S · **Risk:** low

`Context.read_resource()` is typed `async def read_resource(self, uri) -> list[ReadResourceContents]`
— confirmed directly against the installed package, it never returns a string. `prompts.py`'s
`author_recipe` interpolates the raw return value straight into an f-string, so the rendered
prompt literally embeds `[ReadResourceContents(content='{...}', mime_type='application/json')]`
instead of the schema JSON — on every single call. No exception is ever raised (the bare
`except Exception` only catches read *failures*, not "succeeded but returned garbage"), so this
has shipped invisibly; existing tests only exercise the failure branch. Same defect class as
idea #1, found independently in a different, previously-untouched file — **the same bug also
exists a second time**, inside `tools/agentic.py`'s own schema-context fetch (see the
recommended plan's Phase 1 for both sites).

## 4. Fix binary resource reads (PNG/SVGZ diagrams) — value 8/10

**Files:** `snowfakery_mcp/resources/runs.py`, `core/text.py`, `tools/run.py`
**Effort:** S · **Risk:** low

`run_artifact_resource` unconditionally force-decodes every run artifact as UTF-8, including
`diagram.png`/`diagram.svgz` — real binary bytes. Any client that calls
`run_recipe(output_format="png")` and then reads the returned resource URI hits a server-side
crash instead of getting the diagram, despite `MCP_SERVER_SPEC.md` explicitly listing diagram
outputs as in scope. Branch on extension; for binary formats read bytes and let FastMCP's
built-in bytes→`BlobResourceContents` (base64) dispatch handle the wire format — no hand-rolled
encoding needed.

## 5. Fix the `create_app()`/`lifespan()` split-brain; delete dead `_ServerState` — value 8/10

**Files:** `server.py` and every `register_*` function across `tools/*.py`, `resources/*.py`
**Effort:** M · **Risk:** medium

`create_app()` and `lifespan()` each independently construct their own `WorkspacePaths`/`Config`
— one set gets baked into tool closures at registration time, the other is stashed in a
module-level `_ServerState` that **nothing reads** (confirmed zero callers repo-wide). Replace
both with one `lifespan`-decorated async generator yielding `{"paths":..., "config":...}`, have
tools read `ctx.lifespan_context` at call time instead of closing over stale registration-time
values, and delete the vestigial `_ServerState`/`get_paths()`/`get_config()`.

## 6. Replace `MagicMock(spec=FastMCP)` decorator-capture tests with real registration — value 8/10

**Files:** `tests/test_resources_static_unit.py`, `test_tools_examples_extended.py`, `test_resources_templates.py`
**Effort:** M · **Risk:** low

These three test files build a `MagicMock`/`MagicMock(spec=FastMCP)` whose `.tool()`/`.resource()`
`side_effect` just stashes the raw undecorated function in a dict, then call it directly —
never touching FastMCP's real URI-template matching, tag registration, or exception-to-result
conversion. A 3.x decorator or exception-handling change could leave these tests green while
the real server breaks. This is precisely the blind spot that let ideas #1 and #3 ship
undetected. Rewrite to register against a real `fastmcp.FastMCP("test")` instance and assert
through `fastmcp.Client` calls.

## 7. Replace SIGALRM `time_limit()` with per-tool `timeout=` — value 8/10

**Files:** `core/timeout.py`, `server.py`, `tools/run.py`, `tools/mapping.py`, `core/validate.py`
**Effort:** M · **Risk:** medium

`time_limit()` uses raw `signal.SIGALRM`, which its own docstring admits only works in the main
thread on Unix and silently no-ops elsewhere. `iterative_recipe_gen`'s sampling loop has **zero**
timeout coverage today. FastMCP 3.4.2's `timeout=` wraps the call in `anyio.fail_after` and
(combined with default `run_in_thread=True`) dispatches to a worker thread — cross-platform, and
doesn't block the event loop for other requests. Honest caveat: this cancels the *await*, not
the dispatched thread — a truly stuck native call keeps running in the background, same
fundamental limitation as SIGALRM for CPU-bound native code. Still a real portability win, and a
behavior change (`McpError` instead of custom `OperationTimeout`) that needs careful handling.

## 8. Typed models for discovery tools instead of `dict[str, Any]` — value 7/10

**Files:** `tools/capabilities.py`, `examples.py`, `docs.py`, `analyze.py`, `core/types.py`
**Effort:** M · **Risk:** low

Verified live: a `dict[str, Any]` return annotation produces the output schema
`{"additionalProperties": true, "type": "object"}` — no field-level shape at all. 5 of the
server's tools (`list_capabilities`, `list_examples`, `get_example`, `search_docs`,
`analyze_recipe`) use exactly this annotation. These tools already return internally-consistent
shapes; formalizing them as `TypedDict`s costs little and matches the pattern `run_recipe`/
`validate_recipe` already use.

## 9. Serve `get_schema`/schema resource as real JSON, not a stringified blob — value 7/10

**Files:** `tools/docs.py`, `resources/static.py`
**Effort:** S · **Risk:** low

`get_schema` nests the raw schema file text inside `{"uri":..., "schema": "<escaped JSON
string>"}` — a double-encoded JSON Schema. Separately, `recipe_schema_resource` returns a plain
string with no `mime_type`, so FastMCP serves it as `text/plain` even though the payload is
JSON. This directly benefits the tools that read this exact resource for LLM context — the
broken `author_recipe` prompt (#3) and `iterative_recipe_gen` — once fixed together.

## 10. Remove the blanket mypy `ignore_missing_imports` override for `fastmcp.*` — value 7/10

**Files:** `pyproject.toml`, `.github/workflows/ci.yml`
**Effort:** S · **Risk:** low

`pyproject.toml` silences mypy for all of `fastmcp.*` even under `strict = true`, so mypy gives
**zero** signal about fastmcp API compatibility today despite running on every CI push. Splitting
the override (keep it only for `snowfakery.*`, which genuinely lacks stubs) turns mypy into a
real early-warning system for renamed kwargs or Context signature drift — the cheapest possible
addition to the migration's safety net, though it will surface a batch of pre-existing errors to
triage.

## 11. Baseline request/timing observability: `LoggingMiddleware` + `TimingMiddleware` — value 7/10

**Files:** `server.py`, `core/config.py`
**Effort:** S · **Risk:** low

Zero logging or timing exists anywhere in the server today — no way to see how close a
`run_recipe` call got to `timeout_seconds` before being killed. Purely additive:
`app.add_middleware(LoggingMiddleware(...))` / `TimingMiddleware()`. Safe because Snowfakery's
own progress output is already force-routed to stderr (stdio reserves stdout for JSON-RPC), so
Python logging's default stderr handler can't corrupt the transport.

## 12. Consolidate the three duplicated path-safety implementations — value 7/10

**Files:** `resources/templates.py`, `core/paths.py`, `resources/static.py`, `resources/runs.py`, `core/assets.py`
**Effort:** S · **Risk:** low

`resources/templates.py`'s `get_template()` reimplements traversal protection inline instead of
calling the `WorkspacePaths.ensure_within()` it already receives as an argument — a third
hand-rolled version of logic `resources/runs.py` already uses correctly. The quick fix (~4-line
diff, no new API) is the best effort-to-value ratio in this whole list. A further Provider-based
consolidation across all four resource files is real but heavier — FastMCP's built-in
`FileSystemProvider`/`SkillsProvider` aren't drop-in replacements for this codebase's bespoke
path-safety needs, so that's a stretch goal, not a quick win.

## 13. Declare `ToolAnnotations` on every registered tool — value 7/10

**Files:** every file under `tools/`
**Effort:** S · **Risk:** low

Confirmed via grep: zero `@mcp.tool(...)` call sites pass `annotations=` today. Adding accurate
`readOnlyHint`/`idempotentHint`/`openWorldHint` values (discovery tools read-only+idempotent,
`run_recipe`/`generate_mapping` explicitly non-idempotent since each writes a fresh UUID
directory, `iterative_recipe_gen` open-world since it depends on external LLM sampling) is the
standard, protocol-native, essentially-free mechanism for clients to make good UX/safety
decisions — e.g. auto-approving read-only calls but prompting before `run_recipe`. Directly
complementary to, and far cheaper than, the heavier Approval-app and auth ideas ranked lower.
Zero functional risk since annotations are advisory, not enforced.

## 14. Add a `uv`/pip Dependabot ecosystem entry — value 6/10

**File:** `.github/dependabot.yml`
**Effort:** S · **Risk:** low

`.github/dependabot.yml` only watches `github-actions` — there is no pip/uv entry, confirmed by
reading the file. Nothing has ever proposed a PR for a `fastmcp`/`snowfakery`/`openai` release;
this entire migration was surfaced by manual human investigation, not tooling. This is the root
cause underneath idea #10's value proposition — a stricter mypy config only pays off once
something prompts a human to actually run the upgrade. Two-line config change (Dependabot has
had GA `package-ecosystem: "uv"` support since March 2025).

## 15. Typed result unions for `generate_mapping` and `iterative_recipe_gen` — value 6/10

**Files:** `tools/mapping.py`, `tools/agentic.py`, `core/types.py`
**Effort:** M · **Risk:** medium

`generate_mapping` never adopted the `RunResult`-style typed union its siblings use, despite
having the identical ok/error/resources shape — cheap, direct fix. `iterative_recipe_gen`'s bare
`str` return is worse: it conflates three distinct outcomes (validated recipe, fallback error,
"failed after N attempts") into prose a caller must pattern-match. More valuable but riskier,
since it changes the contract of a tool that currently returns freeform text.

## 16. `ResponseLimitingMiddleware` as a defense-in-depth backstop — value 6/10

**Files:** `server.py`, `tools/run.py`, `tools/mapping.py`, `core/text.py`, `core/config.py`
**Effort:** S · **Risk:** low

`truncate()` is only called from `run.py`/`mapping.py`; `analyze_recipe`, `get_example`/
`list_examples`, and `search_docs` have **zero** size cap, and `Config.max_capture_chars` can be
configured up to 5,000,000 with no real ceiling. Should complement, not replace, `truncate()` —
`ResponseLimitingMiddleware` measures the whole serialized result and, if tripped, collapses
everything into one generic text block, destroying fields a client may depend on. Best
configured as a generous last-resort guard, mainly protecting future tools that forget to call
`truncate()`.

## 17. Stream `run_recipe` progress and forward `echo()` messages via `Context` — value 6/10

**Files:** `core/snowfakery_app.py`, `tools/run.py`, `tools/mapping.py`
**Effort:** M · **Risk:** medium

For `reps` up to 100,000 or `target_number.count` up to 10,000,000, the client gets zero
feedback until timeout or completion. Snowfakery's `generate_data()` already calls
`check_if_finished()` on every rep — a real, pre-existing extension point — so bridging it to
`ctx.report_progress()` (via `anyio.from_thread.run(...)`, since generation runs in FastMCP's
threadpool) reuses existing machinery rather than inventing new polling. Main honest risk: this
makes `MCPApplication` per-request stateful and thread-crossing, coupling to FastMCP's
sync-dispatch internals — worth flagging as something to watch across future FastMCP versions.

## 18. Migrate `core/config.py` to `pydantic-settings` — value 5/10

**Files:** `core/config.py`, `tests/test_core_config.py`
**Effort:** S · **Risk:** low

Pure hygiene — no bug fixed. `Config` hand-rolls env parsing/clamping even though `fastmcp`
itself already depends on and uses `pydantic_settings.BaseSettings` for its own `Settings`
classes, so the dependency is already present transitively. The one thing to get right: preserve
today's silent-clamp behavior (a bare `Field(ge=..., le=...)` would raise `ValidationError` at
startup instead) — every call site currently depends on `Config` never raising.

## 19. Enrich `iterative_recipe_gen` with elicitation, capability-gated visibility, session state — value 5/10

**Files:** `tools/agentic.py`, `tools/run.py`, `tools/validate.py`, `server.py`
**Effort:** M · **Risk:** medium

Three related, genuinely-gap-filling but speculative enhancements to the one sampling-dependent
tool: `ctx.elicit()` to ask clarifying questions instead of burning retries on ambiguous goals;
hiding the tool from `tools/list` for clients that don't advertise sampling support (today it's
registered unconditionally and only fails at call time); and `ctx.set_state()` to let a
follow-up call reference a just-generated recipe without re-pasting full YAML. Worth a small
prototype behind a flag, not a launch-blocking item — each piece depends on client support that
may not materialize.

## 20. `FileUpload` provider to ingest client-local recipe files — value 5/10

**Files:** `server.py`, `core/paths.py`, `core/text.py`, `pyproject.toml`
**Effort:** S · **Risk:** low

The one idea in the Apps set that closes an actual capability gap rather than adding cosmetic
UI: today a human using a hosted/remote MCP client has no way to get a recipe that exists only
on their local machine into any tool except by pasting raw YAML. `fastmcp.apps.file_upload.FileUpload`
closes that. Value is real but bounded to human users of Apps-capable clients — coding agents
(the server's dominant caller today) already have direct filesystem access and get zero benefit.

## 21. Auth-provider bootstrap + tag-based authorization, for an eventual HTTP deployment — value 5/10

**Files:** `server.py`, `core/config.py`, `__main__.py`, `main.py`, `tools/run.py`, `tools/mapping.py`
**Effort:** M · **Risk:** medium

Zero authorization surface exists anywhere today — if this server is ever shared across a team,
`run_recipe` becomes an unauthenticated remote code/data-generation endpoint. Honest caveat:
`AuthMiddleware` explicitly no-ops on stdio transport, the server's only transport today, so
this has **zero effect** until the server also moves to HTTP. Day-1 readiness scaffolding, not
an urgent fix — entirely conditional on an HTTP deployment actually happening.

## 22. Opt-in HTTP/streamable-http transport support — value 5/10

**Files:** `server.py`, `main.py`, `__main__.py`, `pyproject.toml`, new `fastmcp.json`/`asgi.py`, `core/paths.py`, `resources/runs.py`
**Effort:** S · **Risk:** low

Today `run()` is a zero-argument `mcp.run()` call with no CLI flags at all. All pieces (CLI
flags, `fastmcp.json`, ASGI mount) are additive and cheap, but genuinely low-urgency — nothing
in the current single-user local-workspace architecture needs a network listener. Worth
explicitly documenting that `stateless_http` is unsafe until run-artifact storage moves off
local disk (a run landing on replica A followed by a read on replica B would 404 today) rather
than reaching for it silently later.

## 23. Adopt FastMCP's own CLI (`fastmcp dev inspector` / `inspect` / `install`) for contributor workflow — value 5/10

**Files:** `main.py`, `__main__.py`, `CONTRIBUTING.md`, `README.md`
**Effort:** S · **Risk:** low

`CONTRIBUTING.md`'s only documented local-run path is `uv run snowfakery-mcp`, which blocks the
terminal with no inspector. Verified live: in 3.4.2, `dev` is a command *group* with two
subcommands (`apps`, `inspector`) — the bare `fastmcp dev <server-spec>` form from 2.x errors
with "Unknown command." The correct invocation is `fastmcp dev inspector <server-spec>`. Pure
DX improvement, doesn't touch how end users install or run the packaged server.

## 24. Approval gate before expensive `run_recipe` calls — value 4/10

**Files:** `server.py`, `tools/run.py`, `core/config.py`
**Effort:** S · **Risk:** low

Genuinely useful UX nudge, but honestly a soft, convention-based gate: `Approval`'s decision
returns only as a chat message that prompts the LLM's next turn, not as state `run_recipe` can
inspect — a model could still call `run_recipe` without ever triggering approval. Real safety
still has to come from `Config`'s existing hard limits.

## 25. Wire native OpenTelemetry tracing behind an env-var toggle — value 4/10

**Files:** `server.py`, `core/config.py`
**Effort:** S · **Risk:** low

FastMCP 3.4.2 already wraps every call in a no-op `server_span()` — nothing to change in this
repo's code for tracing to *exist*, just a way to opt into a real `TracerProvider`/exporter. The
most marginal idea in this list for the server's dominant use case: a local stdio subprocess per
session, with no distributed system to correlate traces across. Worth keeping on the shelf since
it's essentially free, but not worth prioritizing unless the server is ever hosted multi-tenant.

## 26. Adopt `inline-snapshot`/`dirty-equals`; dedupe `get_tool_data()` helper — value 4/10

**Files:** `tests/test_mcp_integration.py`, `test_tools_integration.py`, `conftest.py`, `pyproject.toml`
**Effort:** S · **Risk:** low

Both integration test files define their own copy of `get_tool_data()` and use scattered
`assert "x" in payload` checks rather than full structural assertions. Improves regression
detection for payload-shape drift and removes copy-paste duplication — quality-of-life, not a
safety-net gap the way ranks #1/#3/#6 are.

## 27. `FormInput`-driven structured recipe-goal builder — value 4/10

**Files:** `server.py`, `tools/agentic.py`
**Effort:** M · **Risk:** medium

Real UX polish for human end-users of a chat-driven client, letting them fill a validated form
(tables/row counts/relationships) instead of typing freeform prose. Honest caveat:
`FormInput.on_submit` is a synchronous callable, so it can't itself drive the async
`ctx.sample()` loop — the clean integration is the form composing a goal string that the model
then passes to `iterative_recipe_gen` as a second step. UX scaffolding around an existing tool,
not a capability the server lacks.

## 28. Evaluate FastMCP 3.x background Tasks (`task=True`) for `run_recipe`/`generate_mapping` — value 4/10

**Files:** `tools/run.py`, `tools/mapping.py`, `core/snowfakery_app.py`, `pyproject.toml`
**Effort:** M · **Risk:** medium

Confirmed live: `FastMCP.tool()`'s signature includes a `task: bool | TaskConfig | None`
parameter — a genuinely new call shape not in 2.14.3. Distinct from idea #7 (timeout
enforcement) and #17 (progress notifications): both of those improve a call that's still
guaranteed to hold one request open, while Tasks questions whether it should stay synchronous at
all. More invasive — requires converting tools to async, the `fastmcp[tasks]` extra, and
client-side polling support that's newer and less universally implemented. An evaluate-and-
prototype item, not a guaranteed win.

## 29. Version `run_recipe`/`generate_mapping` with `@mcp.tool(version=...)` — value 3/10

**Files:** `tools/run.py`, `tools/mapping.py`, `tools/agentic.py`
**Effort:** S · **Risk:** low

Cheap insurance for future non-breaking evolution — no tool passes `version=` today, so any
breaking signature change would have to happen in place with no compatibility window. Honestly
low-urgency: one integration surface, no evidence of multiple client versions pinned to
different contracts, no breaking change currently planned. Worth doing opportunistically during
the migration, not a dedicated pass.

## 30. Consult MCP client Roots (`Context.list_roots()`) alongside the static workspace root — value 3/10

**Files:** `core/paths.py`, `server.py`
**Effort:** S · **Risk:** low

`WorkspacePaths.detect()` picks a single root once, before any client connects, from an env var
or the process's launch-time cwd — every path-safety check in the server anchors to that one
static root for the process's whole lifetime. `Context.list_roots()` — confirmed present, zero
call sites anywhere in the repo — exposes the client's own declared project folder(s), which for
editor/IDE-integrated clients can differ from the subprocess's cwd. Genuinely unused capability
mapping onto the server's core security boundary, but speculative and client-dependent — this
server's primary documented clients (Claude Desktop/Code) launch it as a single-purpose local
subprocess and may never send meaningful multi-root data. Worth a small spike (e.g. log a
warning if `list_roots()` disagrees with the configured root), not a load-bearing change.
