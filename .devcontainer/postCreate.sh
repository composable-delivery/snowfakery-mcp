#!/usr/bin/env bash
set -euo pipefail

cd "${PWD}"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Syncing dependencies (all groups)..."
uv sync --all-groups

echo "Done. Try: uv run pytest"
