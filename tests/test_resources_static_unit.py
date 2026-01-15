from importlib.resources.abc import Traversable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.resources.static import register_static_resources


@pytest.fixture
def mock_mcp():
    resources = {}
    mcp = MagicMock()

    def resource(name=None):
        def decorator(func):
            # If name has a template like "snowfakery://examples/{name}", use that as key or simplistic regex
            # For this test, we can just use the name passed or the func name if not
            resources[name] = func
            return func

        return decorator

    mcp.resource.side_effect = resource
    mcp._resources_registry = resources
    return mcp


@pytest.fixture
def mock_paths():
    paths = MagicMock(spec=WorkspacePaths)
    paths.root = Path("/workspace")

    # Mock ensure_within to just return the path if safe
    def ensure_within(base, path):
        if not str(path).startswith(str(base)):
            raise ValueError("Path traversal")
        return path

    paths.ensure_within.side_effect = ensure_within
    return paths


def test_recipe_schema_dev_mode(mock_mcp, mock_paths):
    """Test schema loading from local file (dev mode)."""

    # Setup the path to exist (checked via Path.exists mock)

    with patch("snowfakery_mcp.resources.static.read_text_utf8") as mock_read:
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            mock_read.return_value = "LOCAL_SCHEMA"

            register_static_resources(mock_mcp, mock_paths)

            func = mock_mcp._resources_registry["snowfakery://schema/recipe-jsonschema"]
            result = func()

            assert result == "LOCAL_SCHEMA"
            # Verify we checked the right path
            # Since we patched Path.exists on the class, we can't easily check the instance called
            # But the result confirms it took the if branch.


def test_recipe_schema_bundled_fallback(mock_mcp, mock_paths):
    """Test schema loading from bundled resources (installed mode)."""

    # Setup path to NOT exist
    with patch("pathlib.Path.exists", return_value=False):
        with patch("importlib.resources.files") as mock_files:
            mock_traversable = MagicMock()
            mock_traversable.joinpath.return_value.read_text.return_value = "BUNDLED_SCHEMA"
            mock_files.return_value = mock_traversable

            register_static_resources(mock_mcp, mock_paths)

            func = mock_mcp._resources_registry["snowfakery://schema/recipe-jsonschema"]
            result = func()

            assert result == "BUNDLED_SCHEMA"
            mock_files.assert_called_with("snowfakery_mcp.schema")


def test_examples_path_outside_workspace(mock_mcp, mock_paths):
    """Test examples from a Path outside workspace (e.g. system install)."""

    # Mock examples_root to return a path outside workspace
    external_root = Path("/usr/lib/snowfakery/examples")

    with patch("snowfakery_mcp.resources.static.examples_root", return_value=external_root):
        with patch("snowfakery_mcp.resources.static.read_text_utf8") as mock_read:
            register_static_resources(mock_mcp, mock_paths)

            func = mock_mcp._resources_registry["snowfakery://examples/{name*}"]

            # Setup the specific file existence check
            # Since external path logic doesn't use ensure_within, it uses joinpath manual check?
            # Code: rel = safe_relpath(name); node = root.joinpath(*rel.parts); if node.is_file()...

            # We need to mock is_file on the resulting path object
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.is_dir", return_value=False):
                    mock_read.return_value = "EXAMPLE_CONTENT"
                    result = func(name="basic.yml")
                    assert result == "EXAMPLE_CONTENT"


def test_examples_traversable(mock_mcp, mock_paths):
    """Test examples from a Traversable (zipped/bundled)."""

    # Mock examples_root to return a Traversable (not a Path)
    mock_root = MagicMock(spec=Traversable)
    mock_node = MagicMock(spec=Traversable)
    mock_node.is_file.return_value = True
    mock_node.is_dir.return_value = False
    mock_node.read_text.return_value = "ZIPPED_CONTENT"  # read_text_utf8 handles Traversable?
    # Actually read_text_utf8 in core/text.py might expect Path?
    # Let's check read_text_utf8 implementation.
    # If it calls read_text(encoding='utf-8') it works for Traversable too.

    mock_root.joinpath.return_value = mock_node

    # We need to mock the read_text_utf8 logic effectively or the object passed to it.
    # The code calls read_text_utf8(node).

    with patch("snowfakery_mcp.resources.static.examples_root", return_value=mock_root):
        # We also need to patch safe_relpath to return a simplified path
        with patch("snowfakery_mcp.resources.static.safe_relpath") as mock_safe:
            mock_safe.return_value = Path("basic.yml")

            with patch("snowfakery_mcp.resources.static.read_text_utf8") as mock_read:
                mock_read.return_value = "ZIPPED_CONTENT"

                register_static_resources(mock_mcp, mock_paths)
                func = mock_mcp._resources_registry["snowfakery://examples/{name*}"]

                result = func(name="basic.yml")
                assert result == "ZIPPED_CONTENT"
