# Roadmap

## Phase 0 — Scaffold
- [x] Project layout, packaging (`pyproject.toml`, MIT license)
- [x] Docs: DESIGN, USAGE, ROADMAP
- [x] Example agent YAMLs

## Phase 1 — Core runtime
- [x] Definition parse/validate
- [x] YAML / multi-path / directory loader
- [x] Node registry + builtin nodes
- [x] Graph builder + MetadataAgent runtime
- [x] Public API entrypoints
- [x] CLI (`version`, `list`, `register`, `register-dir`, `run`, `validate`)
- [x] Tests green (pytest)

## Phase 2 — Wheel publish + CLI polish
- [x] Published wheel / internal index distribution (publish tooling + docs; pointing at a real index is ops config)
- [x] CLI UX polish (richer errors, help text)
- [x] Local wheel build (`scripts/build_wheel.sh` / `python -m build`)
- [x] Configurable CLI store via `EDIM_DDE_AI_STORE`

## Phase 3 — Prompt / skill hooks
- [ ] Prompt template hooks for agents
- [ ] Skill / tool registration surface

## Phase 4 — Conditional edges + richer routers
- [x] Conditional edges wired in graph builder (router registry)
- [x] Router factory pattern (config -> RouterFn), aligned with nodes
- [x] `field_truthy` requires `config.field` (no product-specific default)
- [x] Conditional edges use `source` only; reject `from` with migration error
- [ ] Richer router library and YAML sugar

## Phase 5 — Product adoption
- [ ] EDIM RCA agent consumes this wheel
- [ ] Cluster tuning / other product agents migrate

## Backlog / hygiene (revisit later)

- [ ] **`registry/protocols.py` usage check** — Today unused at runtime (concrete modules use `Callable` aliases). Keep for now as contracts for a later **stricter typing** pass (annotate `register_node` / `register_router` / factories with Protocols, or consolidate aliases). At that time: either wire Protocols into signatures **or** remove the file if still redundant. Do not delete preemptively.

## Status

**Current:** Phase 0–2 complete. Local publish capability (wheel/sdist + twine scripts/docs); remote index URL/credentials are an ops step. See Backlog/hygiene for deferred items (e.g. `protocols.py`).

## Execution log

- **2026-07-23** — Renamed project from `edim-ai-foundation` / `edim_ai_foundation`
  to `edim-dde-ai` / `edim_dde_ai` (CLI, env `EDIM_DDE_AI_STORE`, store `~/.edim-dde-ai`,
  display title EDIM DDE AI). Path: `/Users/sabbineni/projects/edim/edim-dde-ai`.

- **2026-07-23** — Phase 2: distribution readiness (`[project.urls]`, classifiers,
  `[release]` extra, `scripts/publish.sh`, `docs/PUBLISHING.md`, `make release`/`publish`)
  and CLI UX polish (help/epilog, `--version`, preflight errors, richer messages/tests).
  Publish-to-index capability delivered; real Artifactory/index wiring remains ops config.

- **2026-07-23** — Router factory refactor: `field_truthy` takes `config.field`;
  `ConditionalEdgeSpec.config`; `get_router_factory` (+ `get_router` alias);
  `source`-only conditional edges; engineer module docstrings; pytest green.

- **2026-07-22** — Phase 0 (scaffold) and Phase 1 (core runtime) completed.
  Package location: `/Users/sabbineni/projects/edim/edim-dde-ai`
  (`edim-dde-ai` / import `edim_dde_ai`).

- **2026-07-22** — Reorganized package into subpackages (`core`, `registry`, `graph`, `api`, `cli`, `nodes`) while keeping the public `edim_dde_ai` API and CLI entry point stable.

- **2026-07-22** — GoF refactor: generic `Registry` base; Strategy catalogs (nodes/chains/routers);
  `GraphBuilder` + adapters; `AgentFactory`; Template Method on `MetadataAgent`; docs updated.
  Public API unchanged; pytest green; wheel rebuilt.

- **2026-07-22** — Added FastAPI-friendly `register_from_dict`, `register_from_json`,
  and `register_from_dicts` public API helpers; docs and tests updated.

