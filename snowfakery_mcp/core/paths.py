from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspacePaths:
    root: Path

    @staticmethod
    def detect() -> WorkspacePaths:
        configured = os.environ.get("SNOWFAKERY_MCP_WORKSPACE_ROOT")
        root = Path(configured).expanduser().resolve() if configured else Path.cwd().resolve()
        return WorkspacePaths(root=root)

    def ensure_within_workspace(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        try:
            resolved.relative_to(self.root)
        except Exception as e:
            raise ValueError(f"Path is outside workspace root: {resolved}") from e
        return resolved

    def ensure_within(self, base_dir: Path, path: Path) -> Path:
        """Resolve `path` and ensure it stays within `base_dir` (and the workspace root)."""

        base_resolved = self.ensure_within_workspace(base_dir)
        resolved = self.ensure_within_workspace(path)
        try:
            resolved.relative_to(base_resolved)
        except Exception as e:
            raise ValueError(f"Path is outside allowed directory: {resolved}") from e
        return resolved

    def runs_root(self) -> Path:
        runs = self.root / ".snowfakery-mcp" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        return runs

    def new_run_dir(self) -> tuple[str, Path]:
        run_id = uuid.uuid4().hex
        run_dir = self.runs_root() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_id, run_dir
