from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.tools.examples import register_example_tools


@pytest.fixture
def mock_mcp_tools():
    mcp = MagicMock(spec=FastMCP)
    tools = {}

    def tool_decorator(**kwargs):
        def decorator(func):
            tools[func.__name__] = func
            return func

        return decorator

    mcp.tool.side_effect = tool_decorator
    return mcp, tools


@pytest.fixture
def mock_paths(tmp_path):
    # Create a mock workspace
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    paths = MagicMock(spec=WorkspacePaths)
    paths.root = workspace_root

    # helper for ensure_within
    def ensure_within(base, path):
        return path

    paths.ensure_within.side_effect = ensure_within

    return paths


def test_get_example_workspace_path(mock_mcp_tools, mock_paths):
    """Test get_example when examples are in the workspace."""
    mcp, tools = mock_mcp_tools
    register_example_tools(mcp, mock_paths)
    get_example = tools["get_example"]

    # Mock examples_root to be a Path inside workspace
    examples_dir = mock_paths.root / "examples"
    examples_dir.mkdir()
    (examples_dir / "test.yml").write_text("content")

    with patch("snowfakery_mcp.tools.examples.examples_root", return_value=examples_dir):
        # Case 1: File exists
        result = get_example("test.yml")
        assert result["content"] == "content"
        assert result["path"] == str(examples_dir / "test.yml")

        # Case 2: File missing
        with pytest.raises(FileNotFoundError):
            get_example("missing.yml")


def test_get_example_bundled_path_outside_workspace(mock_mcp_tools, mock_paths):
    """Test get_example when examples are bundled files (Path) outside workspace."""
    mcp, tools = mock_mcp_tools
    register_example_tools(mcp, mock_paths)
    get_example = tools["get_example"]

    # Mock examples_root to be a Path OUTSIDE workspace.
    # We mock is_relative_to to simulate a path outside the workspace,
    # so it doesn't matter if it exists physically for that check.
    # BUT the code uses .resolve() so we better use a real path.
    # Let's use a separate temp dir.

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        external_root = Path(td)
        (external_root / "test.yml").write_text("external content")
        (external_root / "subdir").mkdir()

        # We need to ensure it's NOT relative to workspace
        # mock_paths.root is likely in /tmp/... too, so they are siblings.

        with patch("snowfakery_mcp.tools.examples.examples_root", return_value=external_root):
            # Case 1: Valid file
            result = get_example("test.yml")
            assert result["content"] == "external content"
            assert result["path"] == "bundled:snowfakery_mcp/bundled_examples/test.yml"

            # Case 2: Directory
            with pytest.raises(IsADirectoryError):
                get_example("subdir")

            # Case 3: Missing
            with pytest.raises(FileNotFoundError):
                get_example("missing.yml")


def test_get_example_traversable(mock_mcp_tools, mock_paths):
    """Test get_example when examples_root returns a Traversable (zip/package)."""
    mcp, tools = mock_mcp_tools
    register_example_tools(mcp, mock_paths)
    get_example = tools["get_example"]

    # Mock Traversable
    # We can use a Mock object that acts like Traversable
    mock_root = MagicMock()
    # It is NOT an instance of Path

    # Setup mock file node
    mock_file = MagicMock()
    mock_file.is_dir.return_value = False
    mock_file.is_file.return_value = True
    # read_text is not called directly, read_text_utf8 is used which handles Path or Traversable
    # We should patch read_text_utf8 to avoid dealing with open() mocks

    # Setup mock dir node
    mock_dir = MagicMock()
    mock_dir.is_dir.return_value = True

    # Setup mock missing node
    mock_missing = MagicMock()
    mock_missing.is_dir.return_value = False
    mock_missing.is_file.return_value = False

    # joinpath logic
    def joinpath(*parts):
        if parts == ("test.yml",):
            return mock_file
        if parts == ("subdir",):
            return mock_dir
        return mock_missing

    mock_root.joinpath.side_effect = joinpath

    with patch("snowfakery_mcp.tools.examples.examples_root", return_value=mock_root):
        with patch(
            "snowfakery_mcp.tools.examples.read_text_utf8", return_value="traversable content"
        ):
            # Case 1: Valid file
            result = get_example("test.yml")
            assert result["content"] == "traversable content"
            assert result["path"] == "bundled:snowfakery_mcp/bundled_examples/test.yml"

            # Case 2: Directory
            with pytest.raises(IsADirectoryError):
                get_example("subdir")

            # Case 3: Missing
            with pytest.raises(FileNotFoundError):
                get_example("missing.yml")
