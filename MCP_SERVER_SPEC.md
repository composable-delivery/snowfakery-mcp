# Server Specification

This document describes the design, capabilities, and tool catalog for the Snowfakery MCP server. It's intended for:

- **Contributors** building new tools or features
- **Integrators** understanding what the server can do
- **Developers** extending or embedding this server

For user-facing documentation, see [README.md](README.md).

## Overview

The Snowfakery MCP server exposes Snowfakery's data generation capabilities through the Model Context Protocol. It enables AI assistants to help users draft, validate, and execute Snowfakery recipes in an iterative workflow.

**Design principle:** Resource-forward — expose real Snowfakery capabilities (language features, examples, schema, execution) as discoverable MCP resources, backed by focused tools and prompts that drive the workflow: draft → validate → run → debug → refine.

## Architecture

### Server name

- `snowfakery-mcp`

### Implementation

- Python server using `fastmcp`
- Embeds Snowfakery as a library (`snowfakery>=4.2.1`)
- Runs in a workspace/project directory with access to bundled Snowfakery docs and examples

### Interaction pattern

The typical workflow:

1. Read relevant resources (schema, examples, docs)
2. Draft or modify recipe text
3. Validate using `validate_recipe` tool
4. Run a small sample with safe stopping criteria
5. If errors occur, inspect them and iterate
6. Adjust stopping criteria and output format for scale

## Scope

### In scope

**Core capabilities:**

- Recipe authoring assistance with schema, docs, and examples
- Recipe validation and error reporting with source locations
- Recipe execution with multiple output formats (text, JSON, CSV, diagrams)
- Static analysis and recipe inspection
- Continuation workflows and CumulusCI mapping generation

**Supported outputs:**

- Text/debug output
- JSON and CSV export
- Diagram outputs (dot, svg, png)
- Continuation files for iterative data generation

### Out of scope (initial)

- Salesforce org mutation or CumulusCI flows
- Full plugin development environment
- Arbitrary database writes via `--dburl` (disabled by default)

## Resources

The server exposes resources in the `snowfakery://` scheme:

### Documentation and schema

- `snowfakery://schema/recipe-jsonschema` — JSON Schema for recipe validation
- `snowfakery://docs/index` — Main language documentation
- `snowfakery://docs/extending` — Plugin authoring guide
- `snowfakery://docs/salesforce` — Salesforce integration concepts
- `snowfakery://docs/embedding` — Embedding Snowfakery in Python applications
- `snowfakery://docs/architecture` — Interpreter architecture notes

### Discovery resources

- `snowfakery://providers/list` — Available Faker providers and methods, organized by category
- `snowfakery://plugins/list` — Built-in Snowfakery plugins with parameters and examples
- `snowfakery://formats/info` — Supported output formats with use cases and dependencies

### Examples

- `snowfakery://examples/list` — Available example recipes
- `snowfakery://examples/{name}` — Individual example recipe

### Run artifacts

- `snowfakery://runs/{run_id}/recipe` — Original recipe
- `snowfakery://runs/{run_id}/stdout` — Debug/text output
- `snowfakery://runs/{run_id}/output.json` — JSON export
- `snowfakery://runs/{run_id}/output.csv` — CSV export
- `snowfakery://runs/{run_id}/csv/` — Directory of CSV files
- `snowfakery://runs/{run_id}/diagram.svg|dot|png` — Diagram outputs
- `snowfakery://runs/{run_id}/continuation.yml` — Continuation file
- `snowfakery://runs/{run_id}/mapping.yml` — CumulusCI mapping

## Tools

### list_capabilities

Returns server version, supported features, and limits.

**Inputs:** none

**Outputs:**

- Snowfakery version
- Supported output formats
- Server limits (max reps, timeouts, output size)

### list_examples

Lists available example recipes.

**Inputs:**

- `prefix` (optional) — filter by name prefix

**Outputs:**

- Example names with short descriptions

### get_example

Retrieves a specific example recipe.

**Inputs:**

- `name` (required)

**Outputs:**

- Recipe text
- Provenance (repo path)

### get_schema

Returns the JSON Schema for recipe validation.

**Inputs:** none

**Outputs:**

- Recipe JSON Schema

### search_docs

Full-text search across Snowfakery documentation.

**Inputs:**

- `query` (required)

**Outputs:**

- Matching documentation sections with snippets

### validate_recipe

Validates a recipe without executing it.

**Inputs:**

- `recipe_text` or `recipe_path`
- `strict_mode` (optional, default: true)

**Outputs:**

- Validation result: `valid` or `invalid`
- Error list with source locations
- Warnings

### analyze_recipe

Performs static analysis on a recipe structure.

**Inputs:**

- `recipe_text` or `recipe_path`

**Outputs:**

- Tables and fields
- Object relationships
- Macros and includes
- Recipe options
- Plugin usage

### run_recipe

Executes a recipe and captures output.

**Inputs:**

- `recipe_text` or `recipe_path`
- `reps` or `target_number` (optional stopping criteria)
- `output_format` (optional, default: `txt`)
- `options` (optional, dict of `--option` values)
- `validate_only` (optional, for validation-only runs)

**Outputs:**

- Execution status (success/failure)
- Resource URI for output
- Error list with messages and line numbers
- Stats (rows generated, runtime)

### generate_mapping

Generates a CumulusCI mapping file from a recipe.

**Inputs:**

- `recipe_text` or `recipe_path`
- `load_declarations_paths` (optional, for extra declarations)

**Outputs:**

- Mapping YAML content
- Resource URI for full mapping

## Safety Model

Snowfakery can read/write files and spawn large generations. The MCP server enforces safe defaults:

### File access

- Limited to explicitly provided paths and workspace root (no `..` escape)
- Server-managed temp outputs

### Execution

- Max row and rep limits (configurable)
- Runtime timeout per run
- Output size cap (truncate + provide file resource for full output)

### Networking

- Disabled by default (can be allowlisted for Salesforce query plugins with explicit opt-in)

### Database

- Write access via `--dburl` is disabled by default

### Data handling

- Continuation files may contain generated values (not secrets)
- Tool results avoid leaking environment variables or secrets
