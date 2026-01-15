from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP

from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.resources.templates import register_template_resources


@pytest.fixture
def mock_mcp_resources():
    mcp = MagicMock(spec=FastMCP)
    resources = {}

    def resource_decorator(uri):
        def decorator(func):
            # simplistic matching for tests
            resources[uri] = func
            return func

        return decorator

    mcp.resource.side_effect = resource_decorator
    return mcp, resources


@pytest.fixture
def mock_paths_with_templates(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()

    # Create structure simulating Snowfakery-Recipe-Templates
    templates_root = root / "Snowfakery-Recipe-Templates" / "snowfakery_samples"
    templates_root.mkdir(parents=True)

    # Add some templates
    (templates_root / "template1.yml").write_text("content1")
    (templates_root / "subdir").mkdir()
    (templates_root / "subdir" / "template2.yml").write_text("content2")

    paths = MagicMock(spec=WorkspacePaths)
    paths.root = root
    return paths


def test_list_templates_success(mock_mcp_resources, mock_paths_with_templates):
    """Test listing templates when directory exists."""
    mcp, resources = mock_mcp_resources
    register_template_resources(mcp, mock_paths_with_templates)

    list_templates = resources["snowfakery://templates/list"]
    result = list_templates()
    data = json.loads(result)

    assert "templates" in data
    templates = data["templates"]
    assert "template1.yml" in templates
    assert "subdir/template2.yml" in templates


def test_list_templates_missing_dir(mock_mcp_resources, tmp_path):
    """Test listing templates when directory is missing."""
    mcp, resources = mock_mcp_resources

    # Paths with just a root, no templates dir inside
    root = tmp_path / "empty_workspace"
    root.mkdir()
    paths = MagicMock(spec=WorkspacePaths)
    paths.root = root

    register_template_resources(mcp, paths)

    list_templates = resources["snowfakery://templates/list"]
    result = list_templates()
    data = json.loads(result)

    assert data["templates"] == []
    assert "note" in data


def test_get_template_success(mock_mcp_resources, mock_paths_with_templates):
    """Test getting a template content."""
    mcp, resources = mock_mcp_resources
    register_template_resources(mcp, mock_paths_with_templates)

    # Note: the key in resources dict is the template pattern "snowfakery://templates/{path_str}"
    # The registered function expects `path_str` argument
    get_template = resources["snowfakery://templates/{path_str}"]

    content = get_template(path_str="template1.yml")
    assert content == "content1"

    content = get_template(path_str="subdir/template2.yml")
    assert content == "content2"


def test_get_template_security(mock_mcp_resources, mock_paths_with_templates):
    """Test path traversal prevention."""
    mcp, resources = mock_mcp_resources
    register_template_resources(mcp, mock_paths_with_templates)
    get_template = resources["snowfakery://templates/{path_str}"]

    with pytest.raises(ValueError, match="Access denied"):
        get_template(path_str="../outside.yml")


def test_get_template_missing(mock_mcp_resources, mock_paths_with_templates):
    """Test fetching missing template."""
    mcp, resources = mock_mcp_resources
    register_template_resources(mcp, mock_paths_with_templates)
    get_template = resources["snowfakery://templates/{path_str}"]

    with pytest.raises(FileNotFoundError):
        get_template(path_str="nonexistent.yml")


def test_get_template_missing_root(mock_mcp_resources, tmp_path):
    """Test fetching template when root dir is missing."""
    mcp, resources = mock_mcp_resources
    root = tmp_path / "empty_workspace"
    root.mkdir()
    paths = MagicMock(spec=WorkspacePaths)
    paths.root = root

    register_template_resources(mcp, paths)
    get_template = resources["snowfakery://templates/{path_str}"]

    with pytest.raises(FileNotFoundError, match="Templates directory not found"):
        get_template(path_str="foo.yml")
