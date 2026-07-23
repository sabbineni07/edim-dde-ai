# Publishing `edim-dde-ai`

This package builds a standard **wheel** and **sdist**. Publish tooling lives in-repo; pointing at a real private index (Artifactory, Azure Artifacts, etc.) is an **ops configuration** step (credentials + URL), not something this repo can do without your environment.

> Placeholders: Homepage / Repository / Documentation URLs in `pyproject.toml` are stubs until the git remote is finalized. This tree may not be under git yet — when ready, `git init`, commit, and tag `v0.1.0` (or your chosen version).

## 1. Local install from a wheel

```bash
./scripts/build_wheel.sh   # or: make release
pip install dist/edim_dde_ai-*.whl
```

Editable install for development:

```bash
pip install -e ".[dev]"
```

## 2. Build wheel + sdist

```bash
make release
# equivalent:
./scripts/build_wheel.sh
# or:
python3 -m build
```

Artifacts land in `dist/` (`.whl` and `.tar.gz`). Requires `build` (`pip install build` or `pip install 'edim-dde-ai[dev]'`).

## 3. Private index (Artifactory / Azure Artifacts / simple HTTP)

Install release tools (do **not** commit secrets):

```bash
pip install 'edim-dde-ai[release]'
# or: pip install -r requirements-release.txt
```

Set credentials via environment (or keyring / `~/.pypirc`):

```bash
export TWINE_REPOSITORY_URL="https://artifactory.example.com/artifactory/api/pypi/pypi-local"
export TWINE_USERNAME="your-user"          # or '__token__' for token auth
export TWINE_PASSWORD="your-password-or-token"

./scripts/publish.sh
# or:
make publish
```

Equivalent with an explicit URL flag:

```bash
./scripts/publish.sh --repository-url "$TWINE_REPOSITORY_URL"
```

Skip rebuild if `dist/` is already fresh:

```bash
./scripts/publish.sh --skip-build
```

## 4. TestPyPI / PyPI (optional)

```bash
./scripts/publish.sh --repository testpypi
# production PyPI (when appropriate):
./scripts/publish.sh --repository pypi
```

Configure credentials in `~/.pypirc` or via `TWINE_USERNAME` / `TWINE_PASSWORD`.

## 5. Install from a private index

```bash
pip install edim-dde-ai \
  --index-url "https://USER:TOKEN@artifactory.example.com/artifactory/api/pypi/pypi-local/simple"
```

Or use a `pip.conf` / `PIP_INDEX_URL` in CI so consumers do not embed tokens in shell history.

## 6. Version bump

1. Edit `src/edim_dde_ai/version.py` (Hatch reads this path).
2. Rebuild: `make release` / `./scripts/build_wheel.sh`.
3. When using git: tag the release, e.g. `git tag v0.1.0` (after `git init` / remote setup if needed).
4. Publish with `./scripts/publish.sh` to your index.

## 7. Capability vs ops

| Done in this repo | Ops / environment |
|-------------------|-------------------|
| `scripts/build_wheel.sh`, `scripts/publish.sh` | Real Artifactory/Azure URL |
| `make release` / `make publish` | `TWINE_*` credentials |
| `docs/PUBLISHING.md`, `[release]` extra | Network allowlists, index ACLs |
| Local wheel + sdist verified | Pointing consumers at `--index-url` |

Publishing to a **real** remote index requires credentials and URL configuration outside this repository.
