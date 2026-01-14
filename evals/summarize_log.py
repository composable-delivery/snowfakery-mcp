from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _get(d: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
    return cur if cur is not None else default


def _short(s: str, n: int = 160) -> str:
    s = " ".join(s.strip().split())
    return s if len(s) <= n else s[: n - 1] + "…"


def summarize(path: Path) -> int:
    data: Any = json.loads(path.read_text(encoding="utf-8"))

    eval_meta: dict[str, Any] = data.get("eval", {}) if isinstance(data, dict) else {}
    model: str = _get(eval_meta, "model", "")
    task: str = _get(eval_meta, "task", "")
    created: str = _get(eval_meta, "created", "")
    base_url: str = _get(eval_meta, "model_base_url", "")

    stats: dict[str, Any] = data.get("stats", {}) if isinstance(data, dict) else {}
    usage: dict[str, Any] = _get(stats, f"model_usage.{model}", {})

    print(f"log: {path}")
    print(f"task: {task}")
    print(f"model: {model}")
    if base_url:
        print(f"base_url: {base_url}")
    if created:
        print(f"created: {created}")

    if isinstance(usage, dict) and usage:
        itok: Any = usage.get("input_tokens")
        otok: Any = usage.get("output_tokens")
        ttok: Any = usage.get("total_tokens")
        print(f"tokens: input={itok} output={otok} total={ttok}")

    samples: list[Any] = data.get("samples", []) if isinstance(data, dict) else []
    if not isinstance(samples, list):
        samples = []

    print(f"samples: {len(samples)}")
    print("-")

    for sample in samples:
        if not isinstance(sample, dict):
            continue

        sid: str = sample.get("id", "")
        output: dict[str, Any] = (
            sample.get("output", {}) if isinstance(sample.get("output"), dict) else {}
        )
        completion: str = str(output.get("completion", ""))

        scores: dict[str, Any] = (
            sample.get("scores", {}) if isinstance(sample.get("scores"), dict) else {}
        )
        scorer: Any = scores.get("snowfakery_mcp_recipe")
        score_value: Any = None
        score_expl: str = ""
        if isinstance(scorer, dict):
            score_value = scorer.get("value")
            score_expl = str(scorer.get("explanation", ""))

        messages: list[Any] = (
            sample.get("messages", []) if isinstance(sample.get("messages"), list) else []
        )
        tool_calls: list[str] = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            if m.get("role") == "tool":
                fn: Any = m.get("function")
                if isinstance(fn, str) and fn:
                    tool_calls.append(fn)

        print(f"sample: {sid}")
        if score_value is not None:
            print(f"score: {score_value} ({_short(score_expl, 240)})")
        if tool_calls:
            print(f"tools: {len(tool_calls)} calls -> {', '.join(tool_calls)}")
        print(f"completion: {_short(completion, 240)}")
        print("-")

    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print("Usage: uv run python evals/summarize_log.py <inspect_log_dump.json>")
        print("Example:")
        print("  uv run inspect log dump logs/<file>.eval > out.json")
        print("  uv run python evals/summarize_log.py out.json")
        return 2

    path = Path(argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    return summarize(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
