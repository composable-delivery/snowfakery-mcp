# Test Coverage Implementation

## Summary

Comprehensive pytest coverage infrastructure has been added to the snowfakery-mcp project.

## What Was Added

### Test Files

1. **Unit Tests** (`tests/test_core_*.py`):
   - `test_core_config.py` — Configuration module tests (8 tests)
   - `test_core_paths.py` — Workspace paths tests (8 tests)
   - `test_core_timeout.py` — Timeout utilities tests (6 tests)
   - `test_core_assets.py` — Asset discovery tests (16 tests)
   - `test_prompts.py` — Prompt generation tests (1 test)
   - `test_server.py` — Server initialization tests (2 tests)

2. **Integration Tests**:
   - `test_tools_integration.py` — Tool MCP integration tests (10 tests)
   - `test_resources.py` — Resource MCP integration tests (8 tests)
   - Enhanced existing `test_mcp_integration_stdio.py`

### Configuration Files

1. **pytest.ini**:
   - Test discovery configuration
   - Asyncio mode configuration for anyio tests
   - Test markers for categorization

2. **pyproject.toml** additions:
   - `[tool.coverage.run]` — Branch coverage, source configuration
   - `[tool.coverage.report]` — Exclude patterns, minimum coverage threshold (75%)
   - `[tool.coverage.html]` — HTML report output directory
   - `[tool.pytest.ini_options]` — Test configuration

3. **.vscode/tasks.json** additions:
   - "Run tests with coverage" — Basic coverage run with fail-under threshold
   - "Generate coverage report (HTML)" — Comprehensive HTML coverage report generation

### Shared Test Utilities

**conftest.py** enhancements:
- `_resource_text()` — Extract text from MCP resource responses
- `_tool_payload_text()` — Extract text from MCP tool results
- `mcp_session` fixture — Pre-configured MCP client session for integration tests

## Coverage Tracking Features

### Coverage Thresholds
- **Minimum coverage**: 75% (enforced in pytest configuration)
- **Branch coverage**: Enabled to catch untested code paths
- **Per-file reporting**: Terminal output shows missing lines for easy navigation

### Coverage Reports

**Terminal Output**:
```bash
uv run pytest --cov=snowfakery_mcp --cov-report=term-missing
```

**HTML Reports**:
```bash
uv run pytest --cov=snowfakery_mcp --cov-report=html:htmlcov
```
- Open `htmlcov/index.html` in browser for interactive coverage view
- Shows line-by-line coverage with execution counts

### VS Code Integration

**Tasks available in Command Palette**:
1. `Tasks: Run Task` → "Run tests with coverage" — Quick coverage check
2. `Tasks: Run Task` → "Generate coverage report (HTML)" — Full HTML report

### CI/CD Integration

The configuration is ready for GitHub Actions or other CI systems:
```bash
uv run pytest --cov=snowfakery_mcp --cov-report=term-missing --cov-fail-under=75
```

## Current Coverage Status

**As of latest test run**: 43.59% (42 passing tests)

**Well-covered modules** (>80%):
- `server.py` — 97.06% (main app creation)
- `prompts.py` — 80.00% (prompt generation)
- `core/text.py` — 85.71% (text utilities)
- `core/timeout.py` — 77.78% (timeout handling)
- `tools/capabilities.py` — 90.00% (capabilities listing)

**Moderate coverage** (50-80%):
- `core/snowfakery_app.py` — 70.00%
- `tools/analyze.py` — 55.56%
- `tools/validate.py` — 50.00%
- `resources/runs.py` — 50.00%

**Lower coverage** (<50%, good candidates for more tests):
- `resources/discovery.py` — 12.12%
- `tools/run.py` — 14.04%
- `tools/examples.py` — 23.21%
- `tools/docs.py` — 25.00%
- `resources/static.py` — 31.71%
- `core/paths.py` — 45.95%
- `core/assets.py` — 45.45%
- `tools/mapping.py` — 45.71%

## Recommended Next Steps

1. **Fix failing tests** — Adjust test assertions to match actual implementation behavior
2. **Add tool-specific tests** — Focus on run.py, examples.py, docs.py for higher coverage
3. **Add resource tests** — More comprehensive discovery and static resource testing
4. **Error path testing** — Test exception handling in all tools
5. **End-to-end recipes** — Create more realistic recipe test cases

## Running Tests

### Quick test:
```bash
uv run pytest tests/
```

### With coverage:
```bash
uv run pytest tests/ --cov=snowfakery_mcp
```

### With detailed missing lines:
```bash
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=term-missing
```

### Generate HTML report:
```bash
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=html
# Then open htmlcov/index.html
```

### Enforce minimum coverage:
```bash
uv run pytest tests/ --cov=snowfakery_mcp --cov-fail-under=75
```

## Test Statistics

- **Total test files**: 7 new + 1 enhanced
- **Total tests**: 42 passing + 25 failing (needs fixing)
- **Test categories**: Unit, Integration, Tool, Resource
- **Coverage tools**: pytest-cov with HTML output
- **Async support**: pytest-anyio for MCP integration tests
