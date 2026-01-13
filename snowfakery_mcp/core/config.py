from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Config:
    timeout_seconds: int
    max_capture_chars: int
    max_reps: int
    max_target_count: int

    @staticmethod
    def from_env() -> "Config":
        return Config(
            timeout_seconds=int(os.environ.get("SNOWFAKERY_MCP_TIMEOUT_SECONDS", "30")),
            max_capture_chars=int(os.environ.get("SNOWFAKERY_MCP_MAX_CAPTURE_CHARS", "20000")),
            max_reps=int(os.environ.get("SNOWFAKERY_MCP_MAX_REPS", "10")),
            max_target_count=int(os.environ.get("SNOWFAKERY_MCP_MAX_TARGET_COUNT", "1000")),
        )
