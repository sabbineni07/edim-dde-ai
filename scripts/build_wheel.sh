#!/usr/bin/env bash
# Build wheel + sdist into dist/. Requires: pip install build  (or edim-dde-ai[dev])
set -euo pipefail
cd "$(dirname "$0")/.."

if ! python3 -c "import build" 2>/dev/null; then
  echo "error: Python package 'build' is required." >&2
  echo "  pip install build" >&2
  echo "  # or: pip install 'edim-dde-ai[dev]'" >&2
  exit 1
fi

rm -rf dist/ build/ *.egg-info src/*.egg-info 2>/dev/null || true
python3 -m build
echo ""
echo "Artifacts:"
ls -la dist/
