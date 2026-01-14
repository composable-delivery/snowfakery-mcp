"""Tests for asset discovery utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from snowfakery_mcp.core.assets import iter_files, safe_relpath


class TestSafeRelpath:
    """Test safe_relpath validation function."""

    def test_valid_simple_filename(self) -> None:
        """Test that simple filenames are accepted."""
        result = safe_relpath("example.yml")
        assert result == Path("example.yml")

    def test_valid_nested_path(self) -> None:
        """Test that nested paths are accepted."""
        result = safe_relpath("subdir/example.yml")
        assert result == Path("subdir/example.yml")

    def test_valid_deeply_nested_path(self) -> None:
        """Test that deeply nested paths are accepted."""
        result = safe_relpath("a/b/c/d/example.yml")
        assert result == Path("a/b/c/d/example.yml")

    def test_rejects_absolute_path(self) -> None:
        """Test that absolute paths are rejected."""
        with pytest.raises(ValueError, match="absolute path"):
            safe_relpath("/etc/passwd")

    def test_rejects_parent_traversal(self) -> None:
        """Test that parent directory traversal is rejected."""
        with pytest.raises(ValueError, match="parent directory"):
            safe_relpath("../etc/passwd")

    def test_rejects_parent_traversal_at_end(self) -> None:
        """Test that paths ending with .. are rejected."""
        with pytest.raises(ValueError, match="parent directory"):
            safe_relpath("subdir/..")

    def test_rejects_parent_traversal_in_middle(self) -> None:
        """Test that paths with .. in the middle are rejected."""
        with pytest.raises(ValueError, match="parent directory"):
            safe_relpath("a/../b")

    def test_rejects_dot_root(self) -> None:
        """Test that lone dot is rejected."""
        with pytest.raises(ValueError, match="traversal|parent directory"):
            safe_relpath(".")

    def test_accepts_hidden_files(self) -> None:
        """Test that hidden files (starting with .) are accepted."""
        result = safe_relpath(".hidden")
        assert result == Path(".hidden")

    def test_accepts_multiple_extensions(self) -> None:
        """Test that files with multiple extensions are accepted."""
        result = safe_relpath("archive.tar.gz")
        assert result == Path("archive.tar.gz")


class TestIterFiles:
    """Test file iteration utilities."""

    def test_iter_files_empty_directory(self, tmp_path: Path) -> None:
        """Test iterating over an empty directory."""
        files = iter_files(tmp_path, suffixes=[".txt"])
        assert files == []

    def test_iter_files_single_file(self, tmp_path: Path) -> None:
        """Test iterating over a directory with one matching file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        files = iter_files(tmp_path, suffixes=[".txt"])
        assert files == ["test.txt"]

    def test_iter_files_multiple_files_same_suffix(self, tmp_path: Path) -> None:
        """Test iterating over multiple files with same suffix."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "file3.txt").write_text("content3")

        files = iter_files(tmp_path, suffixes=[".txt"])
        assert sorted(files) == ["file1.txt", "file2.txt", "file3.txt"]

    def test_iter_files_multiple_suffixes(self, tmp_path: Path) -> None:
        """Test iterating with multiple suffix filters."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.md").write_text("content2")
        (tmp_path / "file3.yml").write_text("content3")
        (tmp_path / "file4.json").write_text("content4")

        files = iter_files(tmp_path, suffixes=[".txt", ".md"])
        assert sorted(files) == ["file1.txt", "file2.md"]

    def test_iter_files_nested_directories(self, tmp_path: Path) -> None:
        """Test iterating over nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.txt").write_text("root")
        (subdir / "nested.txt").write_text("nested")

        files = iter_files(tmp_path, suffixes=[".txt"])
        assert sorted(files) == ["nested.txt", "root.txt"]

    def test_iter_files_ignores_non_matching_suffixes(self, tmp_path: Path) -> None:
        """Test that non-matching files are ignored."""
        (tmp_path / "file.txt").write_text("match")
        (tmp_path / "file.md").write_text("no match")
        (tmp_path / "file").write_text("no match")

        files = iter_files(tmp_path, suffixes=[".txt"])
        assert files == ["file.txt"]

    def test_iter_files_case_sensitive_suffix(self, tmp_path: Path) -> None:
        """Test that suffix matching is case-sensitive."""
        (tmp_path / "file.txt").write_text("match")
        (tmp_path / "file.TXT").write_text("no match by default")

        files = iter_files(tmp_path, suffixes=[".txt"])
        assert files == ["file.txt"]
