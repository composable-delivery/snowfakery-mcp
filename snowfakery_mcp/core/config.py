from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Config:
    timeout_seconds: int
    max_capture_chars: int
    max_reps: int
    max_target_count: int

    @staticmethod
    def from_env() -> Config:
        return Config(
            timeout_seconds=_parse_int_env(
                "SNOWFAKERY_MCP_TIMEOUT_SECONDS",
                default=30,
                min_value=1,
                max_value=600,
            ),
            max_capture_chars=_parse_int_env(
                "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS",
                default=20000,
                min_value=200,
                max_value=5_000_000,
            ),
            max_reps=_parse_int_env(
                "SNOWFAKERY_MCP_MAX_REPS",
                default=10,
                min_value=1,
                max_value=100_000,
            ),
            max_target_count=_parse_int_env(
                "SNOWFAKERY_MCP_MAX_TARGET_COUNT",
                default=1000,
                min_value=1,
                max_value=10_000_000,
            ),
        )


def _parse_int_env(
    name: str,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value
