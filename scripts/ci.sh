#!/usr/bin/env bash
set -euo pipefail

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

uv run --extra dev ruff check .
uv run --extra dev pytest -q
(
  cd docs
  uv run --extra docs make html
)

if rg -n "^data/" .gitignore >/dev/null; then
  echo "data/ ignore guard present"
fi
