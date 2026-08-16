---
name: add-provider-seam
description: Add a Strategy + registry provider seam (retrieval/store/web-style) in edim-dde-ai
agent: agent
argument-hint: Describe the plane name and env var prefix (e.g. FOO / EDIM_FOO)
---

# Add a provider seam

Follow existing patterns in `retrieval/`, `recommendations/`, `store/`, or `web/`:

1. `protocols.py` — Protocol with `name` + operations
2. `models.py` — request/result dataclasses if needed
3. `providers.py` — Null + Memory (+ optional HTTP/cloud) implementations
4. `registry.py` — process-wide get/set + `configure_*_from_env`
5. Package `__init__.py` exports
6. Wire configure in consuming API lifespan only if this plane is host-managed
7. Unit tests with Memory/Null backends
8. Module docstrings (Business purpose / Public API)

Constraints:

- YAML and agents must not import vendor SDKs directly
- Default env backend should be `none` / Null Object
- Fail soft at call sites unless the plane is required for the primary path

Do not change unrelated packages. Update CHANGELOG if the package maintains one.
