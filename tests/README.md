# Snowfakery MCP Test Suite

## Quick Start

```bash
# Run all tests
uv run pytest tests/

# Run with coverage report
uv run pytest tests/ --cov=snowfakery_mcp

# Generate HTML coverage report
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=html
open htmlcov/index.html
```

## Test Organization

### Unit Tests (`tests/test_core_*.py`)

Tests for core utility modules without external dependencies:

- **test_core_config.py** — Configuration reading from environment variables
  - Default values
  - Environment variable overrides
  - Validation and bounds checking

- **test_core_paths.py** — Workspace path handling
  - Path validation and normalization
  - Runs directory management
  - Security checks for path traversal

- **test_core_timeout.py** — Timeout utilities
  - Signal-based timeout implementation
  - Proper cleanup on context exit

- **test_core_assets.py** — File discovery utilities
  - Relative path validation
  - File iteration with suffix filtering
  - Nested directory handling

- **test_prompts.py** — Prompt registration
  - Prompt decorator registration
  - Prompt structure validation

- **test_server.py** — Server initialization
  - App creation and idempotency

### Integration Tests (`tests/test_*_integration.py`)

Tests that exercise the full MCP server via stdio:

- **test_tools_integration.py** — Tool endpoint tests
  - Recipe validation
  - Recipe analysis
  - Recipe execution
  - Example management
  - Capability reporting

- **test_resources.py** — Resource endpoint tests
  - Resource discovery (providers, plugins, formats)
  - Resource content retrieval
  - Schema and documentation access

- **test_mcp_integration_stdio.py** (existing) — Core MCP functionality
  - Tool listing
  - Resource reading
  - Generation and mapping

## Coverage Configuration

### Pytest Configuration

**pytest.ini**:
- Test discovery patterns
- Asyncio configuration
- Test markers

**pyproject.toml** `[tool.coverage.*]`:
- Branch coverage enabled
- Excludes: `__main__.py`, bundled docs/examples
- Minimum threshold: 75%
- HTML reports in `htmlcov/`

### Excluding Code from Coverage

Add `# pragma: no cover` to lines that shouldn't affect coverage:

```python
if TYPE_CHECKING:  # pragma: no cover
    from some_module import Type
```

Common exclusions in pyproject.toml:
- Abstract method definitions
- Representation methods (`__repr__`)
- Main guards (`if __name__ == "__main__"`)
- Type checking blocks

## Running Tests

### Test Selection

```bash
# Run specific test file
uv run pytest tests/test_core_config.py -v

# Run specific test class
uv run pytest tests/test_core_config.py::TestConfigFromEnv -v

# Run specific test
uv run pytest tests/test_core_config.py::TestConfigFromEnv::test_default_config_values -v

# Run tests matching a pattern
uv run pytest tests/ -k "timeout" -v
```

### Coverage Options

```bash
# Show missing lines
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=term-missing

# Show only uncovered lines
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=term-missing:skip-covered

# Branch coverage analysis
uv run pytest tests/ --cov=snowfakery_mcp --cov-report=term-missing --cov-branch

# Generate multiple report formats
uv run pytest tests/ --cov=snowfakery_mcp \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml
```

### Failing on Low Coverage

```bash
# Fail if coverage drops below threshold (from pyproject.toml default: 75%)
uv run pytest tests/ --cov=snowfakery_mcp --cov-fail-under=80
```

## Test Helpers

### MCP Session Fixture

**conftest.py** provides `mcp_session` fixture for integration tests:

```python
@pytest.mark.anyio
async def test_my_tool(mcp_session: ClientSession) -> None:
    out = await mcp_session.call_tool("my_tool", {"param": "value"})
    # Assertions...
```

### Resource/Tool Response Helpers

```python
from tests.conftest import _resource_text, _tool_payload_text

# Extract text from resource responses
res = await mcp_session.read_resource("snowfakery://schema/recipe-jsonschema")
schema = json.loads(_resource_text(res))

# Extract text from tool results
out = await mcp_session.call_tool("validate_recipe", {...})
result = json.loads(_tool_payload_text(out))
```

## VS Code Integration

### Tasks

Open Command Palette (`Cmd+Shift+P`):

- **Run tests with coverage** — Quick test run with coverage
- **Generate coverage report (HTML)** — Full report with navigation
- **Run tests** — Basic test execution
- **Check all** — Format + lint + type check

### Coverage in Editor

With Pylance/Pylance extensions:
- Hover errors show uncovered code paths
- "Inlay hints" can show coverage information
- Use `@pytest.mark.skip` to skip tests during development

## Common Issues

### Tests timeout waiting for server

The MCP server is started as a subprocess. If tests timeout:
- Check that `uv run snowfakery-mcp` works standalone
- Increase `timeout` in `test_mcp_integration_stdio.py`
- Check for deadlocks in server initialization

### Coverage reports are empty

Ensure:
- Tests are actually being run (check output)
- Coverage configuration in `pyproject.toml` is correct
- Source paths match your setup

### Import errors in tests

Run `uv sync` to update dependencies, or:
- Check that `PYTHONPATH` includes the project root
- Verify imports are using correct relative paths

## Adding New Tests

### Test File Template

```python
"""Tests for module_name."""

from __future__ import annotations

import pytest
from snowfakery_mcp.module import function_name


class TestFunctionName:
    """Test function_name functionality."""

    def test_basic_behavior(self) -> None:
        """Test that function does X."""
        result = function_name()
        assert result == expected_value

    def test_error_handling(self) -> None:
        """Test that function raises on invalid input."""
        with pytest.raises(ValueError, match="error message"):
            function_name(invalid_input)
```

### Best Practices

1. **One assertion per test** when possible, multiple when they're testing related behavior
2. **Descriptive test names** that explain what's being tested
3. **Use fixtures** for common setup (see conftest.py)
4. **Mock external dependencies** (filesystem, network, etc.)
5. **Test both happy and error paths**
6. **Use parametrize for similar tests**:

```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

## Performance Considerations

- Tests run in parallel by default with pytest
- Integration tests may be slower due to MCP server startup
- Use `@pytest.mark.slow` for long-running tests
- Profile with `--durations=N` to find slow tests

## Continuous Integration

### GitHub Actions Example

```yaml
- name: Run tests with coverage
  run: uv run pytest tests/ --cov=snowfakery_mcp --cov-fail-under=75

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Plugin](https://pytest-cov.readthedocs.io/)
- [pytest-anyio for Async Tests](https://github.com/magicstack/pytest-anyio)
