#!/usr/bin/env bash
# Build (unless --skip-build) then upload dist/* with twine.
#
# Env (typical private index):
#   TWINE_REPOSITORY_URL   required for a private index unless --repository-url is set
#   TWINE_USERNAME / TWINE_PASSWORD  (or API token / keyring)
#
# Examples:
#   TWINE_REPOSITORY_URL=https://artifactory.example/api/pypi/pypi-local \
#     TWINE_USERNAME=user TWINE_PASSWORD=token ./scripts/publish.sh
#   ./scripts/publish.sh --repository testpypi
#   ./scripts/publish.sh --repository-url https://... --skip-build
set -euo pipefail
cd "$(dirname "$0")/.."

SKIP_BUILD=0
TWINE_ARGS=()

usage() {
  cat <<'USAGE'
Usage: ./scripts/publish.sh [--repository-url URL] [--repository NAME] [--skip-build]

Build wheel+sdist (unless --skip-build), then upload with twine.

Options:
  --repository-url URL   Private/simple index URL (sets twine --repository-url)
  --repository NAME      Named repository from ~/.pypirc (e.g. testpypi, pypi)
  --skip-build           Upload existing dist/ artifacts only
  -h, --help             Show this help

Environment:
  TWINE_REPOSITORY_URL   Alternative to --repository-url for private indexes
  TWINE_USERNAME         Username or '__token__' for token auth
  TWINE_PASSWORD         Password or API token (do not hardcode in scripts)
  TWINE_NON_INTERACTIVE  Set to 1 in CI

Install release tools:
  pip install 'edim-dde-ai[release]'
  # or: pip install build twine
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repository-url)
      [[ $# -ge 2 ]] || { echo "error: --repository-url requires a value" >&2; exit 2; }
      TWINE_ARGS+=(--repository-url "$2")
      shift 2
      ;;
    --repository)
      [[ $# -ge 2 ]] || { echo "error: --repository requires a value" >&2; exit 2; }
      TWINE_ARGS+=(--repository "$2")
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v twine >/dev/null 2>&1 && ! python3 -c "import twine" 2>/dev/null; then
  echo "error: twine is not installed." >&2
  echo "  pip install 'edim-dde-ai[release]'" >&2
  echo "  # or: pip install twine" >&2
  exit 1
fi

# Prefer python -m twine so the active venv is used
TWINE=(python3 -m twine)

has_repo_url=0
for ((i = 0; i < ${#TWINE_ARGS[@]}; i++)); do
  if [[ "${TWINE_ARGS[$i]}" == "--repository-url" ]]; then
    has_repo_url=1
    break
  fi
done
has_repo_name=0
for ((i = 0; i < ${#TWINE_ARGS[@]}; i++)); do
  if [[ "${TWINE_ARGS[$i]}" == "--repository" ]]; then
    has_repo_name=1
    break
  fi
done

if [[ $has_repo_url -eq 0 && $has_repo_name -eq 0 ]]; then
  if [[ -n "${TWINE_REPOSITORY_URL:-}" ]]; then
    TWINE_ARGS+=(--repository-url "$TWINE_REPOSITORY_URL")
  else
    echo "error: set TWINE_REPOSITORY_URL or pass --repository-url / --repository" >&2
    echo "  See docs/PUBLISHING.md" >&2
    exit 2
  fi
fi

if [[ $SKIP_BUILD -eq 0 ]]; then
  ./scripts/build_wheel.sh
else
  if [[ ! -d dist ]] || ! ls dist/*.{whl,tar.gz} >/dev/null 2>&1; then
    echo "error: dist/ has no wheel/sdist; run without --skip-build or ./scripts/build_wheel.sh" >&2
    exit 1
  fi
fi

echo ""
echo "Uploading dist/* with twine..."
"${TWINE[@]}" upload "${TWINE_ARGS[@]}" dist/*
