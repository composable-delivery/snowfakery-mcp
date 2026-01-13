# Snowfakery MCP Server Spec (fastmcp)

## 1. Purpose

Build a Model Context Protocol (MCP) server for authoring, analyzing, debugging, and running Snowfakery recipes.

The design goal is **resource-forward Snowfakery**: the server must expose Snowfakery’s real capabilities (language features, examples, schema, and runnable execution) as discoverable MCP **resources**, plus a set of focused **tools** and **prompts** that drive an iterative workflow (draft → validate → run → debug → refine).

## 2. Scope

### In scope

- Recipe authoring assistance backed by:
  - The Snowfakery recipe JSON Schema
  - Bundled Snowfakery docs and examples
  - Static analysis from Snowfakery’s parser/runtime object model
  - Real execution using the Snowfakery library (same as CLI)
- Recipe validation and error reporting with source locations.
- Recipe execution producing:
  - debug/text output (capture into MCP resources)
  - JSON output (capture)
  - CSV output (workspace directory)
  - diagram outputs (dot/svg/png/etc) when supported
- Continuation workflows (generate continuation file; continue from one).
- Mapping file generation (`--generate-cci-mapping-file`) for CumulusCI use.

### Out of scope (initial)

- Salesforce org mutation / CumulusCI flows.
  - (We can support “read-only query” style plugins later, but default should be no network or no org access.)
- Full plugin development environment management (packaging, publishing).
- Arbitrary database writes via `--dburl` by default.

## 3. Key Inputs (from existing Snowfakery behavior)

### CLI baseline

The Snowfakery CLI supports:

- `snowfakery <recipe.yml>`
- Output formats: `png|svg|svgz|jpeg|jpg|ps|dot|json|txt|csv|sql`
- Options: `--option <name> <value>`
- Stopping criteria: `--target-number/--target-count <count> <TableName>` or `--reps <n>`
- Continuations: `--generate-continuation-file`, `--continuation-file`
- Validation: `--strict-mode`, `--validate-only`
- Mapping file: `--generate-cci-mapping-file`
- Update mode: `--update-input-file`

### API entry point

The server should embed Snowfakery via the public API:

- `snowfakery.api.generate_data(...)`

This provides stable access to:

- output streams / formats
- continuation files
- strict validation

### Recipe language features to support in analysis guidance

The MCP server should help users leverage:

- `object`, `fields`, `friends` (nested object creation)
- `nickname` and `reference` / deep references
- `random_reference` and its RowHistory behavior
- `just_once` singletons
- `macro` and macro layering/overrides
- `include_file` composition
- `option` blocks and `--option` injection
- `for_each` iteration patterns (datasets, schedules)
- Plugins (including search paths and statefulness)

## 4. MCP Server Topology

### Server name

- `snowfakery-mcp`

### Implementation

- Python server using `fastmcp`.
- Imports Snowfakery as a library (`snowfakery>=4.2.1`).

### Runtime assumptions

- Runs in a workspace / project directory.
- Has access to Snowfakery docs/examples bundled in-repo (or installed package fallback).

## 5. Security & Safety Model

Snowfakery can read/write files, spawn large generations, and optionally connect to databases. MCP tooling should be safe-by-default.

### Safety defaults

- File access is limited to:
  - explicitly provided file paths
  - the workspace root (no `..` escape)
  - server-managed temp outputs
- Execution limits:
  - max rows / reps defaults (configurable)
  - max runtime (timeout) per run
  - max output size captured into MCP (truncate + provide file resource for full output)
- Networking:
  - default: no outbound network access in tools
  - allowlist later if needed (e.g., Salesforce query plugins) with explicit opt-in
- Database output (`--dburl`):
  - default disabled unless explicitly enabled by server config

### Redaction

- Continuation files can contain generated values.
- Tool results should avoid leaking environment variables or secrets.

## 6. Core Interaction Pattern

The model should follow an iterative loop:

1. Read relevant resources (schema + examples + docs pages).
2. Draft or modify recipe text.
3. Validate (`validate_recipe` tool).
4. Run a small sample (`run_recipe` tool) with safe stopping criteria.
5. If errors, use `explain_errors` + source mapping and iterate.
6. For scale, adjust stopping criteria and output format.

## 7. Resources (MCP)

The server must provide high-value resources so the model can “learn by looking” and not hallucinate Snowfakery constructs.

### 7.1 Static resources

Recommended URIs (illustrative; final URI scheme is up to the server implementation):

- `snowfakery://schema/recipe-jsonschema`
  - Content: bundled JSON Schema for recipes.
- `snowfakery://docs/index`
  - Content: main Snowfakery language documentation.
- `snowfakery://docs/extending`
  - Content: plugin authoring docs.
- `snowfakery://docs/salesforce`
  - Content: Salesforce integration concepts (read-only guidance).
- `snowfakery://docs/architecture`
  - Content: high-level interpreter architecture notes.
- `snowfakery://examples/list`
  - Content: list of available example recipes.
- `snowfakery://examples/<name>`
  - Content: the example recipe file.

### 7.2 Dynamic / generated resources

These are produced by tools and then exposed as resources.

- `snowfakery://runs/<run_id>/recipe`
- `snowfakery://runs/<run_id>/stdout`
- `snowfakery://runs/<run_id>/output.json`
- `snowfakery://runs/<run_id>/output.sql`
- `snowfakery://runs/<run_id>/csv/` (directory listing + file access)
- `snowfakery://runs/<run_id>/diagram.svg|dot|png`
- `snowfakery://runs/<run_id>/continuation.yml`
- `snowfakery://runs/<run_id>/mapping.yml`

## 8. Tools (MCP)

Tools should be composable and predictable. Prefer:

- accepting either `recipe_path` or `recipe_text`
- returning structured results
- returning resource URIs for large artifacts

Below is the initial tool catalog.

### 8.1 `snowfakery.list_capabilities`

Returns versions and supported features.

Inputs:
- none

Outputs:
- `snowfakery_version`
- supported `output_formats`
- server limits (max reps, timeouts)

### 8.2 `snowfakery.list_examples`

Inputs:
- optional `prefix` filter

Outputs:
- example names + short descriptions (derived from filenames and/or first comment block)

### 8.3 `snowfakery.get_example`

Inputs:
- `name`

Outputs:
- recipe text
- provenance: repo path

### 8.4 `snowfakery.get_schema`

Returns the Snowfakery recipe JSON Schema.

### 8.5 `snowfakery.search_docs`

Inputs:
- `query`
- optional `limit`

Outputs:
- matching snippets with doc path + headings

### 8.6 `snowfakery.validate_recipe`

Validates a recipe without generating output.

Inputs:
- one of:
  - `recipe_path`
  - `recipe_text`
- `strict_mode` (default true)
- `schema_validate` (default true)
- `options`: dict of option name → value (equivalent to `--option`)
- `plugin_options`: dict (equivalent to `--plugin-option`)

Outputs:
- `valid: bool`
- `errors: [ {message, filename, line, column?, kind} ]`
- optional `warnings`

Notes:
- Use Snowfakery’s `validate_only=True` + `strict_mode=True` to ensure parity with CLI behavior.
- When available, use Snowfakery exception metadata (filename/line).

### 8.7 `snowfakery.analyze_recipe`

Static analysis: parse the recipe and return a high-level “explainable” model of what it will generate.

Inputs:
- one of: `recipe_path` or `recipe_text`

Outputs:
- `tables`: inferred tables with inferred fields
- `relationships`: inferred inter-table dependencies (e.g. for mapping generation)
- `uses_random_reference`: tables requiring RowHistory
- `options_declared`: list of `option` definitions
- `plugins_declared`: list of plugin imports
- `estimated_risk`: flags like “unbounded loop possible”, “very high count expression”, etc.

### 8.8 `snowfakery.run_recipe`

Runs Snowfakery and captures output.

Inputs:
- `recipe_path` or `recipe_text`
- `options` dict (maps to `--option`)
- `plugin_options` dict
- stopping criteria:
  - either `reps: int`
  - or `target_number: {table: str, count: int}`
- output selection:
  - `output_format` (default `txt`)
  - one of:
    - `capture_output: true` (returns inline text up to cap + resource for full)
    - `output_file_path` (writes to workspace)
    - `output_folder_path` (csv)
- continuation:
  - `continuation_file_path` (optional)
  - `generate_continuation_file_path` (optional)
- `validate_only` (default false)
- `strict_mode` (default true)

Outputs:
- `run_id`
- `summary` (Snowfakery summary fields, if accessible)
- `stdout_text` (truncated)
- `resources`: list of produced resource URIs

### 8.9 `snowfakery.render_diagram`

Convenience wrapper that sets `output_format` to `dot/svg/png/...` and returns the artifact URI.

### 8.10 `snowfakery.generate_mapping`

Generates a CumulusCI mapping YAML from a recipe.

Inputs:
- `recipe_path` or `recipe_text`
- optional `load_declarations_paths: []`

Outputs:
- mapping YAML text (truncated) + full mapping as a resource

### 8.11 `snowfakery.format_recipe`

Formats YAML in a stable style (optional quality-of-life tool).

Notes:
- This should be purely syntactic formatting, not semantic rewrites.

## 9. Prompts (MCP)

Prompts are “operator playbooks” that encourage the model to use resources + tools correctly.

### 9.1 `author_recipe`

Given a goal (objects, relationships, constraints, volume), produce a recipe with:

- `snowfakery_version: 3`
- options for tunable parameters
- macros / include_file suggestions for reuse

Required behavior:
- consult schema + at least one similar example
- validate before finalizing

### 9.2 `debug_recipe`

Given:

- recipe text
- validation/run error output

The prompt instructs the model to:

- identify the exact failing construct
- propose the smallest change
- re-validate

### 9.3 `explain_recipe`

Explains what a recipe will generate, including inferred tables and relationships.

### 9.4 `refactor_recipe_for_reuse`

Refactor into macros and `include_file`-based libraries.

### 9.5 `build_plugin_stub`

Produces a Snowfakery plugin skeleton (class inheriting from `SnowfakeryPlugin`) plus an example recipe using it.

## 10. Configuration

Server should allow configuration (env vars or config file):

- `SNOWFAKERY_MCP_WORKSPACE_ROOT`
- `SNOWFAKERY_MCP_MAX_REPS`
- `SNOWFAKERY_MCP_MAX_TARGET_COUNT`
- `SNOWFAKERY_MCP_TIMEOUT_SECONDS`
- `SNOWFAKERY_MCP_ALLOW_DBURL` (default false)
- `SNOWFAKERY_MCP_ALLOW_NETWORK` (default false)

## 11. Error Model

Tools should return structured errors. Recommended shape:

```json
{
  "error": {
    "kind": "DataGenValidationError|DataGenSyntaxError|...",
    "message": "...",
    "location": {"filename": "...", "line": 12}
  }
}
```

When `debug_internals`-style tracebacks are available, they should be:

- opt-in
- truncated
- scrubbed for secrets

## 12. MVP Acceptance Criteria

A first version of the MCP server is “useful” when it can:

- Provide schema + core docs + example recipes as resources.
- Validate a recipe and return filename+line errors.
- Run a recipe safely and return output as a resource.
- Produce at least one non-text artifact (JSON or CSV or DOT).
- Support options and stopping criteria (`reps` / `target_number`).

## 13. Future Enhancements

- Richer static analysis (detect unbounded generation patterns).
- Recipe “diff assistant” that proposes minimal patches for errors.
- Optional Salesforce read-only query plugin support with explicit allowlists.
- “Generate from spec” recipes: accept a JSON model of desired tables and constraints.
- CumulusCI integration mode (generate + load orchestration).
