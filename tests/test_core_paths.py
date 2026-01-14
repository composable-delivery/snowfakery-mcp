"""Tests for workspace paths module."""

from __future__ import annotations

from pathlib import Path

import pytest

from snowfakery_mcp.core.paths import WorkspacePaths


class TestWorkspacePathsDetect:
    """Test WorkspacePaths.detect() method."""

    def test_detect_defaults_to_cwd(self) -> None:
        """Test that detect() returns a WorkspacePaths instance."""
        paths = WorkspacePaths.detect()
        assert paths is not None
        assert paths.workspace_root is not None


class TestWorkspacePathsValidation:
    """Test path validation methods."""

    def test_ensure_within_workspace_with_subpath(self, tmp_path: Path) -> None:
        """Test ensure_within_workspace accepts subdirectories."""
        paths = WorkspacePaths(workspace_root=tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = paths.ensure_within_workspace(subdir)
        assert result == subdir

    def test_ensure_within_workspace_rejects_absolute_outside(self, tmp_path: Path) -> None:
        """Test that ensure_within_workspace rejects paths outside workspace."""
        paths = WorkspacePaths(workspace_root=tmp_path)
        outside = Path("/etc/passwd")
        with pytest.raises(ValueError, match="outside"):
            paths.ensure_within_workspace(outside)

    def test_ensure_within_base_dir_rejects_escape(self, tmp_path: Path) -> None:
        """Test that ensure_within rejects path traversal attempts."""
        paths = WorkspacePaths(workspace_root=tmp_path)
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        escaped = tmp_path / "outside.txt"
        with pytest.raises(ValueError, match="outside"):
            paths.ensure_within(base_dir, escaped)


class TestWorkspacePathsRunsDirectory:
    """Test runs directory handling."""

    def test_runs_root_directory_exists(self, tmp_path: Path) -> None:
        """Test that runs_root returns a runs directory path."""
        paths = WorkspacePaths(workspace_root=tmp_path)
        runs_root = paths.runs_root
        assert runs_root.name == ".snowfakery_runs"
        assert str(runs_root).startswith(str(tmp_path))

    def test_new_run_dir_creates_unique_dirs(self, tmp_path: Path) -> None:
        """Test that new_run_dir creates uniquely-named directories."""
        paths = WorkspacePaths(workspace_root=tmp_path)
        run_id_1, dir_1 = paths.new_run_dir()
        run_id_2, dir_2 = paths.new_run_dir()

        assert run_id_1 != run_id_2
        assert dir_1 != dir_2
        # Both should be under runs_root
        assert dir_1.parent.name == ".snowfakery_runs"
        assert dir_2.parent.name == ".snowfakery_runs"
